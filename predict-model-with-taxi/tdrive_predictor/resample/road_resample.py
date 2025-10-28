"""
Road-based resampling (initial version).

Given a sequence of matched candidates with footpoints and timestamps, produce
per-minute samples. If two consecutive matches are on the same edge, interpolate
along the edge geometry; otherwise, interpolate linearly between footpoints as a
fallback (keeps continuity; full path stitching can be added if needed).
"""

from typing import Any, List, Tuple, Optional

import pandas as pd


def resample_on_road(
    matched: List[Optional[dict]],
    ts: List[pd.Timestamp],
    dt_sec: int = 60,
) -> pd.DataFrame:
    """Return DataFrame with columns ['ts','x','y','edge'] on a per-minute grid.

    matched: list of candidate dicts (or None) from HMMMapMatcher.match_trip
    ts: list of timestamps corresponding to matched
    """
    if not matched:
        return pd.DataFrame(columns=['ts', 'x', 'y', 'edge'])
    # build a dense per-minute index within bounds
    t0 = pd.Timestamp(ts[0]).ceil('min')
    t1 = pd.Timestamp(ts[-1]).floor('min')
    idx = pd.date_range(start=t0, end=t1, freq=f'{dt_sec}s')
    if len(idx) == 0:
        return pd.DataFrame(columns=['ts', 'x', 'y', 'edge'])
    # piecewise interpolate between consecutive matched points
    out_rows = []
    # cursor on idx
    j = 0
    for i in range(len(ts) - 1):
        ta = pd.Timestamp(ts[i]); tb = pd.Timestamp(ts[i + 1])
        if tb <= t0:
            continue
        if ta >= t1:
            break
        ma = matched[i]; mb = matched[i + 1]
        # footpoints
        if ma is None:
            xa = None; ya = None; ea = None
        else:
            xa, ya = ma['foot_xy']; ea = ma['edge']
        if mb is None:
            xb = None; yb = None; eb = None
        else:
            xb, yb = mb['foot_xy']; eb = mb['edge']
        # iterate grid times in (max(ta,t0), min(tb,t1)]
        seg_start = max(ta, t0)
        seg_end = min(tb, t1)
        while j < len(idx) and idx[j] <= seg_end:
            tg = idx[j]
            if tg <= seg_start:
                j += 1
                continue
            # linear interpolate by time between footpoints; if same edge and both s exist, could refine
            if xa is None or xb is None:
                # fallback: skip; we will fill later
                out_rows.append({'ts': tg, 'x': None, 'y': None, 'edge': ea})
            else:
                alpha = (tg - ta).total_seconds() / max(1.0, (tb - ta).total_seconds())
                xg = xa + alpha * (xb - xa)
                yg = ya + alpha * (yb - ya)
                # keep edge id of closer endpoint
                edge_g = ea if alpha < 0.5 else eb
                out_rows.append({'ts': tg, 'x': xg, 'y': yg, 'edge': edge_g})
            j += 1
    df = pd.DataFrame(out_rows)
    if df.empty:
        return df
    # fill gaps if any
    df['x'] = df['x'].interpolate().ffill().bfill()
    df['y'] = df['y'].interpolate().ffill().bfill()
    # edge forward fill
    df['edge'] = df['edge'].ffill().bfill()
    return df

