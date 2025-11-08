import os
from typing import List

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from .dataset import SequenceHorizonDataset
from .model import GRUDisplacement, GRUDisplacementRoad, GRUStepDecoderRoad
from .osm.loader import load_graph
from .mapmatch.hmm import CandidateGenerator
from .metrics import compute_errors_m, hit_at_r, per_horizon_errors_m, per_horizon_hit_at_r


def _advance_along_polyline(poly_xy, delta_s: float):
    """Move delta_s meters along a piecewise-linear polyline (array of [[x,y],...])."""
    import math
    if delta_s <= 0.0:
        return float(poly_xy[0,0]), float(poly_xy[0,1])
    rem = float(delta_s)
    for i in range(len(poly_xy) - 1):
        x1,y1 = float(poly_xy[i,0]), float(poly_xy[i,1])
        x2,y2 = float(poly_xy[i+1,0]), float(poly_xy[i+1,1])
        seg = math.hypot(x2-x1, y2-y1)
        if rem <= seg:
            if seg <= 1e-6:
                return x2,y2
            t = rem / seg
            return x1 + t*(x2-x1), y1 + t*(y2-y1)
        rem -= seg
    # beyond end: clamp
    return float(poly_xy[-1,0]), float(poly_xy[-1,1])


def evaluate_gru(
    data_dir: str,
    ckpt_path: str = None,
    lookback: int = None,
    batch_size: int = 128,
    device: str = None,
    mode: str = "xy",
    graphml: str = None,
    place: str = None,
    bbox: tuple = None,
) -> dict:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    meta = pd.read_json(os.path.join(data_dir, 'meta.json'), typ='series').to_dict()
    test_df = pd.read_pickle(os.path.join(data_dir, 'test.pkl'))
    feature_cols: List[str] = meta['feature_cols']
    if ckpt_path is None:
        ckpt_path = os.path.join(data_dir, 'gru_phase_curv.pt' if (mode == 'curv') else ('gru_phase_curv_step.pt' if mode == 'curv_step' else 'gru_phase_a.pt'))
    ckpt = torch.load(ckpt_path, map_location=device)
    if lookback is None:
        lookback = int(ckpt.get('lookback', 20))
    if mode is None:
        mode = ckpt.get('mode', 'xy')
    if mode == 'curv_step':
        return _evaluate_curv_step(test_df, feature_cols, ckpt, device, lookback, graphml, place, bbox, data_dir)
    if mode == 'curv':
        # manual window loop to map Δs→XY
        model = GRUDisplacementRoad(input_size=len(feature_cols))
    else:
        model = GRUDisplacement(input_size=len(feature_cols))
    model.load_state_dict(ckpt['model_state'])
    model.to(device)
    model.eval()
    if mode == 'curv':
        # Build windows and compute XY from Δs predictions using minute polyline
        steps = [1,3,5,10]
        preds_xy = []
        trues_xy = []
        df_sorted = test_df.sort_values(['trip_id','ts']).reset_index(drop=True)
        # If graph args present, use graph-based traversal; else fallback to GT polyline clip
        use_graph = (graphml is not None) or (place is not None) or (bbox is not None)
        G = None
        cand = None
        if use_graph:
            try:
                G = load_graph(graphml_path=graphml, place=place, bbox=bbox)
                cand = CandidateGenerator(G)
            except Exception:
                G = None
                cand = None
                use_graph = False
        for trip_id, g in df_sorted.groupby('trip_id'):
            n = len(g)
            if n < (lookback or 20) + 10:
                continue
            base = g.index.min()
            for end in range(base + (lookback or 20) - 1, base + n):
                max_needed = end + steps[-1]
                if max_needed >= base + n:
                    break
                start = end - ((lookback or 20) - 1)
                x_seq = torch.tensor(df_sorted.loc[start:end, feature_cols].to_numpy(dtype=np.float32)).unsqueeze(0).to(device)
                with torch.no_grad():
                    pred_ds = model(x_seq).squeeze(0).detach().cpu().numpy()  # [4]
                # truths (Δx,Δy) deltas
                path_xy = df_sorted.loc[end:max_needed, ['x','y']].to_numpy(dtype=np.float64)
                x0 = float(path_xy[0,0]); y0=float(path_xy[0,1])
                true_xy = []
                for h in steps:
                    tx = float(path_xy[h,0]-x0); ty=float(path_xy[h,1]-y0)
                    true_xy.extend([tx, ty])
                trues_xy.append(np.array(true_xy, dtype=np.float32))
                # predictions
                if use_graph and ('edge' in df_sorted.columns):
                    cur_edge = df_sorted.loc[end, 'edge']
                    cur_s = df_sorted.loc[end, 's'] if 's' in df_sorted.columns else None
                    if (cur_edge is None) or (cur_s is None) or (not np.isfinite(cur_s)):
                        # project to nearest edge
                        cands = cand.query(x0, y0)
                        if cands:
                            cur_edge = cands[0]['edge']
                            cur_s = cands[0]['s']
                        else:
                            cur_edge = None
                    # determine direction from last minute heading vs tangent
                    dir_sign = 1.0
                    if cur_edge is not None and cur_s is not None and end-1 >= base:
                        import math
                        dxh = float(df_sorted.loc[end,'x'] - df_sorted.loc[end-1,'x'])
                        dyh = float(df_sorted.loc[end,'y'] - df_sorted.loc[end-1,'y'])
                        h_obs = math.atan2(dyh, dxh)
                        h_tan = cand.tangent_heading(cur_edge, float(cur_s)) or h_obs
                        dhead = ((h_tan - h_obs + math.pi) % (2*math.pi)) - math.pi
                        dir_sign = 1.0 if abs(math.cos(dhead)) >= 0.0 else 1.0
                    pred_xy = []
                    # traverse per horizon independently from base
                    for h_idx, h in enumerate(steps):
                        total = float(max(0.0, pred_ds[h_idx])) * float(dir_sign)
                        e = cur_edge
                        s0 = float(cur_s) if cur_s is not None else 0.0
                        rem = total
                        px, py = x0, y0
                        steps_guard = 0
                        while rem > 1e-6 and e is not None and steps_guard < 16:
                            steps_guard += 1
                            # advance on current edge
                            try:
                                data = G.get_edge_data(*e)
                                geom = data.get('geometry', None)
                            except Exception:
                                geom = None
                            if geom is None:
                                # straight line fallback
                                u,v,k = e
                                x1 = G.nodes[u]['x']; y1=G.nodes[u]['y']
                                x2 = G.nodes[v]['x']; y2=G.nodes[v]['y']
                                import math
                                L = math.hypot(x2-x1, y2-y1)
                                Lrem = max(0.0, L - s0)
                                step = min(rem, Lrem)
                                t = 0.0 if L<=1e-6 else (s0 + step) / L
                                px = x1 + t*(x2-x1); py = y1 + t*(y2-y1)
                                rem -= step
                                if rem <= 1e-6:
                                    break
                                # move to next edge at v
                                at = v
                            else:
                                L = float(geom.length)
                                Lrem = max(0.0, L - s0)
                                step = min(rem, Lrem)
                                sg = s0 + step
                                p = geom.interpolate(sg)
                                px, py = float(p.x), float(p.y)
                                rem -= step
                                if rem <= 1e-6:
                                    break
                                # at end of edge
                                u,v,k = e
                                at = v
                            # choose next edge by alignment
                            neigh = cand.neighbor_edges(e)
                            best = None; best_sc = -1e18
                            import math
                            h1 = cand.tangent_heading(e, s0 if geom is None else float(L)) or 0.0
                            for en in neigh:
                                if en == e:
                                    continue
                                # if edge starts at current node, use s≈0; else s≈len
                                u2,v2,k2 = en
                                if u2 == at:
                                    h2 = cand.tangent_heading(en, 0.0) or 0.0
                                elif v2 == at:
                                    # reverse direction (leaving from v2 backwards)
                                    # approximate heading at end
                                    # Note: CandidateGenerator.tangent_heading assumes forward; we reuse end heading
                                    # and still move forward along its own orientation in next loop by resetting s0
                                    h2 = cand.tangent_heading(en, float(G.get_edge_data(u2,v2,k2).get('geometry', None).length) if G.get_edge_data(u2,v2,k2).get('geometry', None) is not None else 0.0) or 0.0
                                else:
                                    continue
                                align = abs(math.cos(((h2 - h1 + math.pi) % (2*math.pi)) - math.pi))
                                if align > best_sc:
                                    best_sc = align; best = en
                            e = best
                            # reset s0 at new edge start
                            if e is None:
                                break
                            u3,v3,k3 = e
                            if u3 == at:
                                s0 = 0.0
                            else:
                                # start from end (approximate)
                                data2 = G.get_edge_data(u3,v3,k3)
                                geom2 = data2.get('geometry', None)
                                s0 = float(geom2.length) if geom2 is not None else 0.0
                        pred_xy.extend([px - x0, py - y0])
                    preds_xy.append(np.array(pred_xy, dtype=np.float32))
                else:
                    # Fallback: use ground-truth polyline clip method
                    import math
                    # total path length
                    total_len = 0.0
                    for i in range(len(path_xy)-1):
                        dx = path_xy[i+1,0]-path_xy[i,0]; dy = path_xy[i+1,1]-path_xy[i,1]
                        total_len += math.hypot(dx,dy)
                    pred_ds = np.clip(pred_ds, 0.0, total_len)
                    pred_xy = []
                    for h_idx, h in enumerate(steps):
                        px, py = _advance_along_polyline(path_xy[:h+1], float(pred_ds[h_idx]))
                        pred_xy.extend([px - x0, py - y0])
                    preds_xy.append(np.array(pred_xy, dtype=np.float32))
        if not preds_xy:
            return {"ADE": float('nan'), "FDE": float('nan'), "Hit@100": float('nan'), "Hit@200": float('nan'), "Hit@400": float('nan')}
        preds_t = torch.tensor(np.vstack(preds_xy))
        targets_t = torch.tensor(np.vstack(trues_xy))
        res = compute_errors_m(preds_t, targets_t)
        res['Hit@100'] = hit_at_r(preds_t, targets_t, radius_m=100.0, final_only=True)
        res['Hit@200'] = hit_at_r(preds_t, targets_t, radius_m=200.0, final_only=True)
        res['Hit@400'] = hit_at_r(preds_t, targets_t, radius_m=400.0, final_only=True)
        ph_err = per_horizon_errors_m(preds_t, targets_t)
        ph_hit200 = per_horizon_hit_at_r(preds_t, targets_t, radius_m=200.0)
        res['PerHorizonError'] = {'h1': ph_err[0], 'h3': ph_err[1], 'h5': ph_err[2], 'h10': ph_err[3]}
        res['PerHorizonHit@200'] = {'h1': ph_hit200[0], 'h3': ph_hit200[1], 'h5': ph_hit200[2], 'h10': ph_hit200[3]}
        # optional CSV outputs (per-horizon and slices by speed/stop)
        try:
            ph = []
            for i,k in enumerate(['h1','h3','h5','h10']):
                ph.append({'h': k, 'error_m': res['PerHorizonError'][k], 'hit@200': res['PerHorizonHit@200'][k]})
            pd.DataFrame(ph).to_csv(os.path.join(data_dir, 'per_horizon_curv.csv'), index=False)
        except Exception:
            pass
    else:
        ds_test = SequenceHorizonDataset(test_df, feature_cols, lookback=lookback)
        dl_test = DataLoader(ds_test, batch_size=batch_size, shuffle=False, num_workers=0)
        preds = []
        targets = []
        # collect slice features (v, stop_flag) per window end in dataset order
        df_sorted = test_df.sort_values(['trip_id','ts']).reset_index(drop=True)
        slice_v = []
        slice_stop = []
        # rebuild windows to align with dataset ordering
        ex_v = []
        ex_stop = []
        for trip_id, g in df_sorted.groupby('trip_id'):
            n = len(g)
            if n < (lookback or 20) + 10:
                continue
            base_idx = g.index.min()
            for end in range(base_idx + (lookback or 20) - 1, base_idx + n):
                max_needed = end + 10
                if max_needed >= base_idx + n:
                    break
                ex_v.append(float(df_sorted.loc[end, 'v']) if 'v' in df_sorted.columns else 0.0)
                ex_stop.append(int(df_sorted.loc[end, 'stop_flag']) if 'stop_flag' in df_sorted.columns else 0)
        with torch.no_grad():
            for x_seq, y_target, base_pos in dl_test:
                y_pred = model(x_seq.to(device))
                preds.append(y_pred.cpu())
                targets.append(y_target)
        if not preds:
            return {"ADE": float('nan'), "FDE": float('nan'), "Hit@100": float('nan'), "Hit@200": float('nan'), "Hit@400": float('nan')}
        preds = torch.cat(preds, dim=0)
        targets = torch.cat(targets, dim=0)
        res = compute_errors_m(preds, targets)
        res['Hit@100'] = hit_at_r(preds, targets, radius_m=100.0, final_only=True)
        res['Hit@200'] = hit_at_r(preds, targets, radius_m=200.0, final_only=True)
        res['Hit@400'] = hit_at_r(preds, targets, radius_m=400.0, final_only=True)
        # per-horizon diagnostics
        ph_err = per_horizon_errors_m(preds, targets)  # [h1,h3,h5,h10]
        ph_hit200 = per_horizon_hit_at_r(preds, targets, radius_m=200.0)
        res['PerHorizonError'] = {'h1': ph_err[0], 'h3': ph_err[1], 'h5': ph_err[2], 'h10': ph_err[3]}
        res['PerHorizonHit@200'] = {'h1': ph_hit200[0], 'h3': ph_hit200[1], 'h5': ph_hit200[2], 'h10': ph_hit200[3]}
        # optional CSV outputs
        try:
            ph = []
            for i,k in enumerate(['h1','h3','h5','h10']):
                ph.append({'h': k, 'error_m': res['PerHorizonError'][k], 'hit@200': res['PerHorizonHit@200'][k]})
            pd.DataFrame(ph).to_csv(os.path.join(data_dir, 'per_horizon_xy.csv'), index=False)
            # slices by speed terciles
            v_arr = np.array(ex_v, dtype=np.float32)
            n = len(v_arr)
            if n == preds.shape[0]:
                cuts = np.quantile(v_arr, [0.33, 0.66]) if n > 10 else [np.median(v_arr), np.median(v_arr)]
                bins = np.digitize(v_arr, cuts)
                rows = []
                for b in [0,1,2]:
                    mask = (bins == b)
                    if mask.sum() == 0:
                        continue
                    p_b = preds[mask]
                    t_b = targets[mask]
                    r = compute_errors_m(p_b, t_b)
                    r['Hit@200'] = hit_at_r(p_b, t_b, radius_m=200.0, final_only=True)
                    rows.append({'bucket': b, 'count': int(mask.sum()), 'ADE': r['ADE'], 'FDE': r['FDE'], 'Hit@200': r['Hit@200']})
                if rows:
                    pd.DataFrame(rows).to_csv(os.path.join(data_dir, 'slices_speed_xy.csv'), index=False)
                # slices by stop_flag
                stop_arr = np.array(ex_stop, dtype=np.int32)
                rows2 = []
                for sv in [0,1]:
                    mask = (stop_arr == sv)
                    if mask.sum() == 0:
                        continue
                    p_b = preds[mask]
                    t_b = targets[mask]
                    r = compute_errors_m(p_b, t_b)
                    r['Hit@200'] = hit_at_r(p_b, t_b, radius_m=200.0, final_only=True)
                    rows2.append({'stop_flag': sv, 'count': int(mask.sum()), 'ADE': r['ADE'], 'FDE': r['FDE'], 'Hit@200': r['Hit@200']})
                if rows2:
                    pd.DataFrame(rows2).to_csv(os.path.join(data_dir, 'slices_stop_xy.csv'), index=False)
        except Exception:
            pass
    print("Per-horizon mean error (m):", {k: round(v, 2) for k, v in res['PerHorizonError'].items()})
    print("Per-horizon Hit@200:", {k: round(v, 3) for k, v in res['PerHorizonHit@200'].items()})
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()})
    return res

def _evaluate_curv_step(test_df, feature_cols, ckpt, device, lookback, graphml, place, bbox, data_dir):
    from .osm.loader import load_graph
    from .mapmatch.hmm import CandidateGenerator
    import numpy as np
    import torch
    model = GRUStepDecoderRoad(input_size=len(feature_cols))
    model.load_state_dict(ckpt['model_state'])
    model.to(device)
    model.eval()
    steps_all = list(range(1, 11))
    steps_eval = [1, 3, 5, 10]
    preds_xy = []
    trues_xy = []
    df_sorted = test_df.sort_values(['trip_id','ts']).reset_index(drop=True)
    use_graph = (graphml is not None) or (place is not None) or (bbox is not None)
    G = None; cand = None
    if use_graph:
        try:
            G = load_graph(graphml_path=graphml, place=place, bbox=bbox)
            cand = CandidateGenerator(G)
        except Exception:
            use_graph = False
    for trip_id, g in df_sorted.groupby('trip_id'):
        n = len(g)
        if n < (lookback or 20) + max(steps_all):
            continue
        base_idx = g.index.min()
        for end in range(base_idx + (lookback or 20) - 1, base_idx + n):
            if end + max(steps_all) >= base_idx + n:
                break
            x_seq = torch.tensor(df_sorted.loc[end-(lookback or 20)+1:end, feature_cols].to_numpy(dtype=np.float32)).unsqueeze(0).to(device)
            with torch.no_grad():
                pred_steps = model(x_seq).squeeze(0).detach().cpu().numpy()
            x0 = float(df_sorted.loc[end, 'x']); y0 = float(df_sorted.loc[end, 'y'])
            true_xy = []
            for h in steps_eval:
                tx = float(df_sorted.loc[end+h, 'x'] - x0); ty = float(df_sorted.loc[end+h, 'y'] - y0)
                true_xy.extend([tx, ty])
            trues_xy.append(np.array(true_xy, dtype=np.float32))
            if use_graph and ('edge' in df_sorted.columns):
                cur_edge = df_sorted.loc[end, 'edge'] if 'edge' in df_sorted.columns else None
                cur_s = df_sorted.loc[end, 's'] if 's' in df_sorted.columns else None
                if (cur_edge is None) or (cur_s is None) or (not np.isfinite(cur_s)):
                    cands0 = cand.query(x0, y0)
                    if cands0:
                        cur_edge = cands0[0]['edge']
                        cur_s = cands0[0]['s']
                    else:
                        cur_edge = None
                pred_xy_list = []
                px, py = x0, y0
                e = cur_edge
                s0 = float(cur_s) if cur_s is not None else 0.0
                import math
                for si in range(len(steps_all)):
                    rem = float(max(0.0, pred_steps[si]))
                    steps_guard = 0
                    while rem > 1e-6 and e is not None and steps_guard < 16:
                        steps_guard += 1
                        try:
                            data = G.get_edge_data(*e)
                            geom = data.get('geometry', None)
                        except Exception:
                            geom = None
                        if geom is None:
                            u,v,k = e
                            x1 = G.nodes[u]['x']; y1=G.nodes[u]['y']
                            x2 = G.nodes[v]['x']; y2=G.nodes[v]['y']
                            L = math.hypot(x2-x1, y2-y1)
                            Lrem = max(0.0, L - s0)
                            step = min(rem, Lrem)
                            t = 0.0 if L<=1e-6 else (s0 + step) / L
                            px = x1 + t*(x2-x1); py = y1 + t*(y2-y1)
                            rem -= step
                            if rem <= 1e-6:
                                break
                            at = v
                        else:
                            L = float(geom.length)
                            Lrem = max(0.0, L - s0)
                            step = min(rem, Lrem)
                            sg = s0 + step
                            p = geom.interpolate(sg)
                            px, py = float(p.x), float(p.y)
                            rem -= step
                            if rem <= 1e-6:
                                break
                            u,v,k = e
                            at = v
                        neigh = cand.neighbor_edges(e)
                        best = None; best_sc = -1e18
                        h1 = cand.tangent_heading(e, s0 if geom is None else float(L)) or 0.0
                        for en in neigh:
                            if en == e:
                                continue
                            u2,v2,k2 = en
                            if u2 == at:
                                h2 = cand.tangent_heading(en, 0.0) or 0.0
                            elif v2 == at:
                                data2 = G.get_edge_data(u2,v2,k2)
                                geom2 = data2.get('geometry', None)
                                h2 = cand.tangent_heading(en, float(geom2.length) if geom2 is not None else 0.0) or 0.0
                            else:
                                continue
                            align = abs(math.cos(((h2 - h1 + math.pi) % (2*math.pi)) - math.pi))
                            if align > best_sc:
                                best_sc = align; best = en
                        e = best
                        if e is None:
                            break
                        u3,v3,k3 = e
                        if u3 == at:
                            s0 = 0.0
                        else:
                            data3 = G.get_edge_data(u3,v3,k3)
                            geom3 = data3.get('geometry', None)
                            s0 = float(geom3.length) if geom3 is not None else 0.0
                    pred_xy_list.append((px - x0, py - y0))
                agg = []
                for h in steps_eval:
                    dx, dy = pred_xy_list[h-1]
                    agg.extend([dx, dy])
                preds_xy.append(np.array(agg, dtype=np.float32))
            else:
                path_xy = df_sorted.loc[end:end+max(steps_all), ['x','y']].to_numpy(dtype=np.float64)
                import math
                pred_xy_list = []
                cur_idx = 0
                cur_off = 0.0
                for si in range(len(steps_all)):
                    rem = float(max(0.0, pred_steps[si]))
                    xA,yA = path_xy[cur_idx]
                    if cur_idx+1 < len(path_xy):
                        xB,yB = path_xy[cur_idx+1]
                    else:
                        xB,yB = xA,yA
                    seg_len = math.hypot(xB-xA, yB-yA)
                    posx, posy = xA, yA
                    while rem > 1e-6 and cur_idx+1 < len(path_xy):
                        avail = max(0.0, seg_len - cur_off)
                        step = min(rem, avail)
                        t = 0.0 if seg_len<=1e-6 else (cur_off + step)/seg_len
                        posx = xA + t*(xB-xA); posy = yA + t*(yB-yA)
                        rem -= step
                        if rem <= 1e-6:
                            cur_off += step
                            break
                        cur_idx += 1
                        cur_off = 0.0
                        xA,yA = path_xy[cur_idx]
                        if cur_idx+1 < len(path_xy):
                            xB,yB = path_xy[cur_idx+1]
                        else:
                            xB,yB = xA,yA
                        seg_len = math.hypot(xB-xA, yB-yA)
                    pred_xy_list.append((posx - x0, posy - y0))
                agg = []
                for h in steps_eval:
                    dx, dy = pred_xy_list[h-1]
                    agg.extend([dx, dy])
                preds_xy.append(np.array(agg, dtype=np.float32))
    if not preds_xy:
        return {"ADE": float('nan'), "FDE": float('nan'), "Hit@100": float('nan'), "Hit@200": float('nan'), "Hit@400": float('nan')}
    preds_t = torch.tensor(np.vstack(preds_xy))
    targets_t = torch.tensor(np.vstack(trues_xy))
    res = compute_errors_m(preds_t, targets_t)
    res['Hit@100'] = hit_at_r(preds_t, targets_t, radius_m=100.0, final_only=True)
    res['Hit@200'] = hit_at_r(preds_t, targets_t, radius_m=200.0, final_only=True)
    res['Hit@400'] = hit_at_r(preds_t, targets_t, radius_m=400.0, final_only=True)
    ph_err = per_horizon_errors_m(preds_t, targets_t)
    ph_hit200 = per_horizon_hit_at_r(preds_t, targets_t, radius_m=200.0)
    res['PerHorizonError'] = {'h1': ph_err[0], 'h3': ph_err[1], 'h5': ph_err[2], 'h10': ph_err[3]}
    res['PerHorizonHit@200'] = {'h1': ph_hit200[0], 'h3': ph_hit200[1], 'h5': ph_hit200[2], 'h10': ph_hit200[3]}
    return res


