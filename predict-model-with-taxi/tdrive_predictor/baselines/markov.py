"""
Markov baseline over road segments (no semantics).

Builds a time-of-day (hour) conditioned transition model over edges, using
per-minute sequences (Phase B resampled data). At inference, rolls out the
most probable edge per minute and outputs positions as edge midpoints.
"""

from collections import defaultdict, Counter
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from ..mapmatch.hmm import CandidateGenerator


EdgeKey = Tuple[int, int, int]


def _edge_midpoint(graph: Any, edge: EdgeKey) -> Tuple[float, float]:
    u, v, key = edge
    data = graph.get_edge_data(u, v, key)
    geom = data.get('geometry', None)
    if geom is None:
        ux = graph.nodes[u]['x']
        uy = graph.nodes[u]['y']
        vx = graph.nodes[v]['x']
        vy = graph.nodes[v]['y']
        return (0.5 * (ux + vx), 0.5 * (uy + vy))
    p = geom.interpolate(0.5 * geom.length)
    return (float(p.x), float(p.y))


def _assign_edges(df: pd.DataFrame, cand_gen: CandidateGenerator) -> List[EdgeKey]:
    edges: List[EdgeKey] = []
    for _, row in df.iterrows():
        cands = cand_gen.query(float(row['x']), float(row['y']))
        if cands:
            edges.append(cands[0]['edge'])
        else:
            # dummy edge as None-like; will be skipped in transitions
            edges.append((-1, -1, -1))
    return edges


def build_transitions(train_df: pd.DataFrame, cand_gen: CandidateGenerator, laplace: float = 0.1, enable_stay: bool = True) -> List[Dict[EdgeKey, Counter]]:
    """Build hour-conditioned transitions from per-minute train data.

    Returns a list of 24 dicts: trans[hour][edge_a] -> Counter(edge_b->count)
    """
    trans: List[Dict[EdgeKey, Counter]] = [defaultdict(Counter) for _ in range(24)]
    print(f"[Markov] Building transitions on train set | rows={len(train_df)}")
    trip_count = 0
    for trip_id, g in train_df.sort_values(['trip_id', 'ts']).groupby('trip_id'):
        g = g.reset_index(drop=True)
        edges = _assign_edges(g[['x', 'y']], cand_gen)
        stop = g['stop_flag'].values if 'stop_flag' in g.columns else None
        for i in range(len(g) - 1):
            a = edges[i]
            b = edges[i + 1]
            if a[0] == -1 or b[0] == -1:
                continue
            hour = int(g['ts'].iloc[i].hour)
            # stay (self-loop) when stopped
            if enable_stay and stop is not None and stop[i] == 1:
                trans[hour][a][a] += 1
            else:
                trans[hour][a][b] += 1
        trip_count += 1
        if trip_count % 1000 == 0:
            print(f"[Markov]   processed {trip_count} train trips...")
    total_states = sum(len(hour_dict) for hour_dict in trans)
    total_transitions = sum(sum(counter.values()) for hour_dict in trans for counter in hour_dict.values())
    print(f"[Markov] Finished transitions | states={total_states} | transitions={total_transitions}")
    return trans


def _argmax_next(trans_hour: Dict[EdgeKey, Counter], a: EdgeKey, alpha: float = 0.1) -> EdgeKey:
    if a not in trans_hour or not trans_hour[a]:
        return a
    counts = trans_hour[a]
    # Laplace smoothing over observed neighbors
    total = sum(counts.values()) + alpha * len(counts)
    best_b = None
    best_p = -1.0
    for b, c in counts.items():
        p = (c + alpha) / total
        if p > best_p:
            best_p = p
            best_b = b
    return best_b if best_b is not None else a


def eval_markov_on_split(
    graph: Any,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    cand_gen: CandidateGenerator,
    lookback: int = 20,
) -> Tuple[np.ndarray, np.ndarray]:
    """Evaluate Markov baseline: returns (y_pred, y_true) arrays like other baselines.

    Uses per-minute dataframes; maps each row to nearest edge; builds transitions
    on train; at test time, rolls out per minute choosing argmax next edge per hour.
    Positions are taken as edge midpoints for simplicity.
    """
    print(f"[Markov] Starting evaluation | train_rows={len(train_df)} | test_rows={len(test_df)} | lookback={lookback}")
    trans = build_transitions(train_df, cand_gen)
    steps = [1, 3, 5, 10]
    preds: List[List[float]] = []
    truths: List[List[float]] = []
    trip_count = 0
    for trip_id, g in test_df.sort_values(['trip_id', 'ts']).groupby('trip_id'):
        g = g.reset_index(drop=True)
        n = len(g)
        if n < lookback + max(steps):
            continue
        edges = _assign_edges(g[['x', 'y']], cand_gen)
        for end in range(lookback - 1, n - max(steps)):
            # base time and edge
            base_ts = pd.Timestamp(g['ts'].iloc[end])
            a = edges[end]
            # base pos (x0,y0)
            x0 = float(g['x'].iloc[end])
            y0 = float(g['y'].iloc[end])
            # simulate minute-by-minute
            sim_edge = a
            # cache predicted XY per step
            xy_cache: Dict[int, Tuple[float, float]] = {}
            for s in range(1, max(steps) + 1):
                hour = int((base_ts + pd.Timedelta(minutes=s - 1)).hour)
                sim_edge = _argmax_next(trans[hour], sim_edge)
                px, py = _edge_midpoint(graph, sim_edge)
                xy_cache[s] = (px, py)
            # build y_pred/y_true
            y_pred_row: List[float] = []
            y_true_row: List[float] = []
            for s in steps:
                px, py = xy_cache[s]
                y_pred_row.extend([px - x0, py - y0])
                row = g.iloc[end + s]
                y_true_row.extend([float(row['x'] - x0), float(row['y'] - y0)])
            preds.append(y_pred_row)
            truths.append(y_true_row)
        trip_count += 1
        if trip_count % 500 == 0:
            print(f"[Markov]   processed {trip_count} test trips...")
    if not preds:
        print("[Markov] No valid windows found on test set (preds empty).")
        return np.zeros((0, 8), dtype=np.float32), np.zeros((0, 8), dtype=np.float32)
    print(f"[Markov] Completed evaluation windows | count={len(preds)}")
    return np.array(preds, dtype=np.float32), np.array(truths, dtype=np.float32)
