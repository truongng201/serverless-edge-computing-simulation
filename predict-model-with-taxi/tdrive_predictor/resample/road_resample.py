"""
Road-based resampling (stitched, curvilinear where possible).

Given a sequence of matched candidates with footpoints and timestamps, produce
per-minute samples. Cases per interval [t_i, t_{i+1}]:
  - Same edge: interpolate along the edge geometry by curvilinear coordinate s.
  - Adjacent edges (share a node): stitch across the shared node by traversing
    the tail of edge i then the head of edge i+1, split by curvilinear distance.
  - Otherwise: fallback to linear interpolation between footpoints.
"""

from typing import Any, List, Tuple, Optional

import pandas as pd
from shapely.geometry import LineString


def _edge_geom(graph: Any, edge: Tuple[int, int, int]) -> LineString:
    u, v, k = edge
    data = graph.get_edge_data(u, v, k)
    geom = data.get('geometry', None)
    if geom is None:
        ux = graph.nodes[u]['x']; uy = graph.nodes[u]['y']
        vx = graph.nodes[v]['x']; vy = graph.nodes[v]['y']
        geom = LineString([(ux, uy), (vx, vy)])
    return geom


def _shared_node(e1: Tuple[int, int, int], e2: Tuple[int, int, int]) -> Optional[int]:
    u1, v1, _ = e1; u2, v2, _ = e2
    s = {u1, v1}.intersection({u2, v2})
    if not s:
        return None
    return list(s)[0]


def resample_on_road(
    matched: List[Optional[dict]],
    ts: List[pd.Timestamp],
    graph: Any,
    dt_sec: int = 60,
) -> pd.DataFrame:
    """Return DataFrame with columns ['ts','x','y','edge'] on a per-minute grid.

    matched: list of candidate dicts (or None) from HMMMapMatcher.match_trip
    ts: list of timestamps corresponding to matched
    graph: projected (meters) MultiDiGraph with edge geometries
    """
    if not matched:
        return pd.DataFrame(columns=['ts', 'x', 'y', 'edge'])
    t0 = pd.Timestamp(ts[0]).ceil('min')
    t1 = pd.Timestamp(ts[-1]).floor('min')
    idx = pd.date_range(start=t0, end=t1, freq=f'{dt_sec}s')
    if len(idx) == 0:
        return pd.DataFrame(columns=['ts', 'x', 'y', 'edge'])

    out_rows = []
    j = 0
    for i in range(len(ts) - 1):
        ta = pd.Timestamp(ts[i]); tb = pd.Timestamp(ts[i + 1])
        if tb <= t0:
            continue
        if ta >= t1:
            break
        ma = matched[i]; mb = matched[i + 1]
        # basic footpoints and edge info
        if ma is None:
            xa = ya = None; ea = None; sa = None; la = None
        else:
            xa, ya = ma['foot_xy']; ea = ma['edge']; sa = float(ma['s']); la = float(ma['edge_len'])
        if mb is None:
            xb = yb = None; eb = None; sb = None; lb = None
        else:
            xb, yb = mb['foot_xy']; eb = mb['edge']; sb = float(mb['s']); lb = float(mb['edge_len'])

        seg_start = max(ta, t0)
        seg_end = min(tb, t1)
        while j < len(idx) and idx[j] <= seg_end:
            tg = idx[j]
            if tg <= seg_start:
                j += 1
                continue
            alpha = (tg - ta).total_seconds() / max(1.0, (tb - ta).total_seconds())

            if xa is not None and xb is not None and ea is not None and eb is not None:
                if ea == eb and sa is not None and sb is not None:
                    # same edge: interpolate along s
                    geom = _edge_geom(graph, ea)
                    sg = sa + alpha * (sb - sa)
                    sg = min(max(sg, 0.0), geom.length)
                    pg = geom.interpolate(sg)
                    out_rows.append({'ts': tg, 'x': float(pg.x), 'y': float(pg.y), 'edge': ea, 's': float(sg), 'edge_len': float(geom.length)})
                else:
                    # try stitching across shared node
                    sh = _shared_node(ea, eb)
                    if sh is not None and sa is not None and sb is not None:
                        geom_a = _edge_geom(graph, ea)
                        geom_b = _edge_geom(graph, eb)
                        # distance from sa to the closer end to shared node on A
                        u1, v1, _ = ea; u2, v2, _ = eb
                        # end index on A toward shared node
                        end_len_a = 0.0 if sh == u1 else geom_a.length
                        # choose direction that reaches shared node
                        if sh == u1:
                            L1 = abs(sa - 0.0)
                        else:
                            L1 = abs(geom_a.length - sa)
                        # on B from shared node to sb
                        start_len_b = 0.0 if sh == u2 else geom_b.length
                        if sh == u2:
                            L2 = abs(sb - 0.0)
                        else:
                            L2 = abs(geom_b.length - sb)
                        Ltot = max(1e-6, L1 + L2)
                        dist = alpha * Ltot
                        if dist <= L1:
                            # still on A
                            if sh == u1:
                                sg = max(0.0, sa - dist)
                            else:
                                sg = min(geom_a.length, sa + dist)
                            pg = geom_a.interpolate(sg)
                            out_rows.append({'ts': tg, 'x': float(pg.x), 'y': float(pg.y), 'edge': ea, 's': float(sg), 'edge_len': float(geom_a.length)})
                        else:
                            # moved onto B
                            rem = dist - L1
                            if sh == u2:
                                sg = min(geom_b.length, 0.0 + rem)
                            else:
                                sg = max(0.0, geom_b.length - rem)
                            pg = geom_b.interpolate(sg)
                            out_rows.append({'ts': tg, 'x': float(pg.x), 'y': float(pg.y), 'edge': eb, 's': float(sg), 'edge_len': float(geom_b.length)})
                    else:
                        # fallback linear in XY
                        xg = xa + alpha * (xb - xa)
                        yg = ya + alpha * (yb - ya)
                        edge_g = ea if alpha < 0.5 else eb
                        out_rows.append({'ts': tg, 'x': xg, 'y': yg, 'edge': edge_g, 's': None, 'edge_len': None})
            else:
                # missing match; leave None for fill later
                out_rows.append({'ts': tg, 'x': None, 'y': None, 'edge': ea, 's': None, 'edge_len': None})
            j += 1

    df = pd.DataFrame(out_rows)
    if df.empty:
        return df
    # normalize dtypes then fill any residual gaps
    try:
        df = df.infer_objects(copy=False)
    except Exception:
        pass
    for c in ['x', 'y', 's', 'edge_len']:
        if c in df.columns:
            try:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            except Exception:
                pass
    df['x'] = df['x'].interpolate().ffill().bfill()
    df['y'] = df['y'].interpolate().ffill().bfill()
    df['edge'] = df['edge'].ffill().bfill()
    # For rows without s/edge_len (fallback linear), project point to edge to recover s if possible
    try:
        from shapely.geometry import Point
        missing = df['s'].isna()
        if missing.any():
            for idx in df[missing].index:
                e = df.at[idx, 'edge']
                if e is None:
                    continue
                geom = _edge_geom(graph, e)
                p = Point(df.at[idx, 'x'], df.at[idx, 'y'])
                sg = float(geom.project(p))
                df.at[idx, 's'] = sg
                df.at[idx, 'edge_len'] = float(geom.length)
    except Exception:
        pass
    return df
