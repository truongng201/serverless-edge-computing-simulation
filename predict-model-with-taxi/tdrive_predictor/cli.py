import argparse
import os

from .prepare import prepare_phase_a, prepare_phase_b
from .train import train_gru
from .evaluate import evaluate_gru
from .baselines.ctrv import eval_ctrv_on_split, CTRVParams
from .metrics import compute_errors_m, hit_at_r
from .osm.loader import load_graph
from .baselines.markov import eval_markov_on_split


def main():
    parser = argparse.ArgumentParser(prog='tdrive_predictor', description='T-Drive Phase A pipeline')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_prep = sub.add_parser('prepare', help='Prepare Phase A dataset')
    p_prep.add_argument('--tdrive-root', type=str, required=True,
                        help='Path to taxi_log_2008_by_id directory')
    # default artifacts in cwd to avoid nested predict-model-with-taxi paths
    p_prep.add_argument('--out-dir', type=str, default='tdrive_predictor_artifacts/phase_a')
    p_prep.add_argument('--num-taxis', type=int, default=500)
    p_prep.add_argument('--max-idle-gap-min', type=int, default=15,
                        help='Gap (minutes) to split trips; increase if sampling is sparse')
    p_prep.add_argument('--use-osm', action='store_true', help='Enable Phase B with OSM map-matching')
    p_prep.add_argument('--graphml', type=str, default=None, help='Path to cached OSM GraphML file')
    p_prep.add_argument('--xml', type=str, default=None, help='Path to local OSM XML (.osm/.xml) to build graph from (offline)')
    p_prep.add_argument('--place', type=str, default=None, help='Place name for OSMnx (e.g., "Beijing, China")')
    p_prep.add_argument('--bbox', type=float, nargs=4, default=None, metavar=('NORTH','SOUTH','EAST','WEST'),
                        help='Bounding box for OSMnx graph download')
    p_prep.add_argument('--cand-radius-m', type=float, default=50.0, help='Candidate search radius (m)')
    p_prep.add_argument('--k-candidates', type=int, default=5, help='Max candidates per observation')
    p_prep.add_argument('--sigma-gps-m', type=float, default=12.0, help='GPS sigma for emission (m)')
    p_prep.add_argument('--use-shortest-path', action='store_true', help='Use graph shortest-path for transitions')
    p_prep.add_argument('--overpass-endpoint', type=str, default=None, help='Custom Overpass API endpoint URL')
    p_prep.add_argument('--overpass-timeout', type=int, default=None, help='Overpass timeout (seconds)')

    p_train = sub.add_parser('train', help='Train GRU baseline for Phase A')
    p_train.add_argument('--data-dir', type=str, default='tdrive_predictor_artifacts/phase_a')
    p_train.add_argument('--lookback', type=int, default=20)
    p_train.add_argument('--batch-size', type=int, default=64)
    p_train.add_argument('--hidden-size', type=int, default=128)
    p_train.add_argument('--num-layers', type=int, default=1)
    p_train.add_argument('--dropout', type=float, default=0.1)
    p_train.add_argument('--lr', type=float, default=1e-3)
    p_train.add_argument('--epochs', type=int, default=10)

    p_eval = sub.add_parser('eval', help='Evaluate GRU on test set')
    p_eval.add_argument('--data-dir', type=str, default='tdrive_predictor_artifacts/phase_a')
    p_eval.add_argument('--ckpt', type=str, default=None)
    p_eval.add_argument('--lookback', type=int, default=None)

    p_ctrv = sub.add_parser('eval-ctrv', help='Evaluate CTRV EKF baseline on test set')
    p_ctrv.add_argument('--data-dir', type=str, default='tdrive_predictor_artifacts/phase_a')
    p_ctrv.add_argument('--lookback', type=int, default=20)
    p_ctrv.add_argument('--r-pos', type=float, default=20.0)
    p_ctrv.add_argument('--q-pos', type=float, default=0.5)
    p_ctrv.add_argument('--q-v', type=float, default=0.5)
    p_ctrv.add_argument('--q-psi', type=float, default=0.01)
    p_ctrv.add_argument('--q-omega', type=float, default=0.005)
    p_ctrv.add_argument('--snap', action='store_true', help='Snap rollout points to nearest road (requires OSM graph)')
    p_ctrv.add_argument('--graphml', type=str, default=None)
    p_ctrv.add_argument('--place', type=str, default=None)
    p_ctrv.add_argument('--bbox', type=float, nargs=4, default=None, metavar=('NORTH','SOUTH','EAST','WEST'))
    p_ctrv.add_argument('--cand-radius-m', type=float, default=30.0)
    p_ctrv.add_argument('--k-candidates', type=int, default=3)

    p_markov = sub.add_parser('eval-markov', help='Evaluate Markov baseline on road segments (Phase B data recommended)')
    p_markov.add_argument('--data-dir', type=str, default='tdrive_predictor_artifacts/phase_b')
    p_markov.add_argument('--lookback', type=int, default=20)
    p_markov.add_argument('--graphml', type=str, default=None)
    p_markov.add_argument('--place', type=str, default=None)
    p_markov.add_argument('--bbox', type=float, nargs=4, default=None, metavar=('NORTH','SOUTH','EAST','WEST'))
    p_markov.add_argument('--cand-radius-m', type=float, default=50.0)
    p_markov.add_argument('--k-candidates', type=int, default=5)

    args = parser.parse_args()
    if args.cmd == 'prepare':
        if args.use_osm:
            prepare_phase_b(
                tdrive_root=args.tdrive_root,
                out_dir=args.out_dir,
                num_taxis=args.num_taxis,
                max_idle_gap_min=args.max_idle_gap_min,
                graphml=args.graphml,
                place=args.place,
                bbox=tuple(args.bbox) if args.bbox is not None else None,
                overpass_endpoint=args.overpass_endpoint,
                overpass_timeout=args.overpass_timeout,
                candidate_radius_m=args.cand_radius_m,
                k_candidates=args.k_candidates,
                sigma_gps_m=args.sigma_gps_m,
                use_shortest_path=args.use_shortest_path,
                xml=args.xml,
            )
        else:
            prepare_phase_a(
                tdrive_root=args.tdrive_root,
                out_dir=args.out_dir,
                num_taxis=args.num_taxis,
                max_idle_gap_min=args.max_idle_gap_min,
            )
    elif args.cmd == 'train':
        ckpt = train_gru(
            data_dir=args.data_dir,
            lookback=args.lookback,
            batch_size=args.batch_size,
            hidden_size=args.hidden_size,
            num_layers=args.num_layers,
            dropout=args.dropout,
            lr=args.lr,
            epochs=args.epochs,
        )
        print(f"Saved checkpoint: {ckpt}")
    elif args.cmd == 'eval':
        stats = evaluate_gru(data_dir=args.data_dir, ckpt_path=args.ckpt, lookback=args.lookback)
        print("Metrics:", stats)
    elif args.cmd == 'eval-ctrv':
        import os, pandas as pd, numpy as np
        test_df = pd.read_pickle(os.path.join(args.data_dir, 'test.pkl'))
        params = CTRVParams(
            r_pos=args.r_pos,
            q_pos=args.q_pos,
            q_v=args.q_v,
            q_psi=args.q_psi,
            q_omega=args.q_omega,
        )
        y_pred, y_true = eval_ctrv_on_split(test_df, lookback=args.lookback, params=params)
        # optional snap-to-road per predicted step
        if args.snap:
            if args.graphml is None and args.place is None and args.bbox is None:
                raise SystemExit('--snap requires --graphml or --place/--bbox to load OSM graph')
            G = load_graph(graphml_path=args.graphml, place=args.place, bbox=tuple(args.bbox) if args.bbox else None)
            from .mapmatch.hmm import CandidateGenerator
            cand = CandidateGenerator(G, radius_m=args.cand_radius_m, k=args.k_candidates)
            # snap each predicted displacement to nearest road around base pos incrementally
            import torch
            pred_t = torch.tensor(y_pred)
            true_t = torch.tensor(y_true)
            # reconstruct absolute positions per row and step
            # We need base positions from test_df windows; rebuild windows inline
            steps = [1,3,5,10]
            abs_preds = []
            abs_trues = []
            from .dataset import SequenceHorizonDataset
            meta = pd.read_json(os.path.join(args.data_dir, 'meta.json'), typ='series').to_dict()
            feature_cols = meta['feature_cols']
            ds = SequenceHorizonDataset(test_df, feature_cols, lookback=args.lookback)
            import numpy as np
            idx = 0
            for trip_id, g in test_df.sort_values(['trip_id','ts']).groupby('trip_id'):
                g = g.reset_index(drop=True)
                n = len(g)
                if n < args.lookback + max(steps):
                    continue
                for end in range(args.lookback - 1, n - max(steps)):
                    x0 = float(g['x'].iloc[end]); y0=float(g['y'].iloc[end])
                    # accumulate per-minute predicted positions
                    base = (x0, y0)
                    # expand pred_t row to per-step
                    row_pred = pred_t[idx].numpy().reshape(4,2)
                    # generate per-minute by repeating nearest per-step; to keep simple, snap horizons only
                    snapped = []
                    for h,(dx,dy) in zip(steps, row_pred):
                        px,py = base[0]+dx, base[1]+dy
                        cands = cand.query(px,py)
                        if cands:
                            fxy = cands[0]['foot_xy']
                            snapped.append((fxy[0]-base[0], fxy[1]-base[1]))
                        else:
                            snapped.append((dx,dy))
                    abs_preds.append(np.array(snapped).reshape(-1))
                    # truths unchanged
                    row_true = true_t[idx].numpy()
                    abs_trues.append(row_true)
                    idx += 1
            y_pred = np.array(abs_preds, dtype=np.float32)
            y_true = np.array(abs_trues, dtype=np.float32)
            pred_t = torch.tensor(y_pred)
            true_t = torch.tensor(y_true)
        import torch
        pred_t = torch.tensor(y_pred)
        true_t = torch.tensor(y_true)
        res = compute_errors_m(pred_t, true_t)
        res['Hit@100'] = hit_at_r(pred_t, true_t, radius_m=100.0, final_only=True)
        res['Hit@200'] = hit_at_r(pred_t, true_t, radius_m=200.0, final_only=True)
        res['Hit@400'] = hit_at_r(pred_t, true_t, radius_m=400.0, final_only=True)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()})
        print("Metrics:", res)
    elif args.cmd == 'eval-markov':
        import os, pandas as pd, numpy as np
        train_df = pd.read_pickle(os.path.join(args.data_dir, 'train.pkl'))
        test_df = pd.read_pickle(os.path.join(args.data_dir, 'test.pkl'))
        G = load_graph(graphml_path=args.graphml, place=args.place, bbox=tuple(args.bbox) if args.bbox else None)
        from .mapmatch.hmm import CandidateGenerator
        cand = CandidateGenerator(G, radius_m=args.cand_radius_m, k=args.k_candidates)
        y_pred, y_true = eval_markov_on_split(G, train_df, test_df, cand, lookback=args.lookback)
        import torch
        pred_t = torch.tensor(y_pred)
        true_t = torch.tensor(y_true)
        res = compute_errors_m(pred_t, true_t)
        res['Hit@100'] = hit_at_r(pred_t, true_t, radius_m=100.0, final_only=True)
        res['Hit@200'] = hit_at_r(pred_t, true_t, radius_m=200.0, final_only=True)
        res['Hit@400'] = hit_at_r(pred_t, true_t, radius_m=400.0, final_only=True)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()})
        print("Metrics:", res)


if __name__ == '__main__':
    main()
