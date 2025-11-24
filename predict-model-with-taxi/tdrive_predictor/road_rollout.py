"""Utilities for graph-constrained rollout of curv_step predictions.

This module centralizes the logic for traversing the road graph step by
step given a starting edge/curvilinear coordinate and a sequence of
predicted curvilinear displacements (Δs). It is shared between offline
evaluation and online inference.
"""
from typing import Any, Iterable, List, Tuple

import math
import numpy as np

from .mapmatch.hmm import CandidateGenerator


def rollout_curv_step_on_graph(
    graph: Any,
    cand: CandidateGenerator,
    edge_t,
    s_t: float,
    ds_seq: Iterable[float],
    x0: float,
    y0: float,
    max_hops_per_step: int = 16,
) -> List[Tuple[float, float]]:
    """Roll out curv_step Δs sequence on the road graph.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        Road graph in projected coordinates.
    cand : CandidateGenerator
        Helper providing neighbor_edges and tangent_heading utilities.
    edge_t :
        Current edge identifier (u, v, key) at time t. May be None.
    s_t : float
        Current curvilinear position along edge_t (meters from u).
    ds_seq : iterable of float
        Predicted step-wise curvilinear displacements (meters per minute).
    x0, y0 : float
        Base position at time t (meters). Used for initialization and
        to derive absolute coordinates.
    max_hops_per_step : int
        Safety cap on the number of edge transitions per step.

    Returns
    -------
    coords : list[(x, y)]
        Absolute on-graph coordinates after each step in ds_seq.
    """
    px, py = float(x0), float(y0)
    e = edge_t
    try:
        s0 = float(s_t) if s_t is not None and np.isfinite(s_t) else 0.0
    except Exception:
        s0 = 0.0
    coords: List[Tuple[float, float]] = []
    for ds in ds_seq:
        rem = float(max(0.0, ds))
        steps_guard = 0
        while rem > 1e-6 and e is not None and steps_guard < max_hops_per_step:
            steps_guard += 1
            try:
                data = graph.get_edge_data(*e)
                geom = data.get("geometry", None)
            except Exception:
                geom = None
            if geom is None:
                u, v, k = e
                x1 = graph.nodes[u]["x"]
                y1 = graph.nodes[u]["y"]
                x2 = graph.nodes[v]["x"]
                y2 = graph.nodes[v]["y"]
                L = math.hypot(x2 - x1, y2 - y1)
                Lrem = max(0.0, L - s0)
                step = min(rem, Lrem)
                t = 0.0 if L <= 1e-6 else (s0 + step) / L
                px = x1 + t * (x2 - x1)
                py = y1 + t * (y2 - y1)
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
                u, v, k = e
                at = v
            # choose next edge by alignment with current tangent
            neigh = cand.neighbor_edges(e)
            best = None
            best_sc = -1e18
            h1 = cand.tangent_heading(e, s0 if geom is None else float(L)) or 0.0
            for en in neigh:
                if en == e:
                    continue
                u2, v2, k2 = en
                if u2 == at:
                    h2 = cand.tangent_heading(en, 0.0) or 0.0
                elif v2 == at:
                    data2 = graph.get_edge_data(u2, v2, k2)
                    geom2 = data2.get("geometry", None)
                    h2 = cand.tangent_heading(
                        en, float(geom2.length) if geom2 is not None else 0.0
                    ) or 0.0
                else:
                    continue
                align = abs(math.cos(((h2 - h1 + math.pi) % (2 * math.pi)) - math.pi))
                if align > best_sc:
                    best_sc = align
                    best = en
            e = best
            if e is None:
                break
            u3, v3, k3 = e
            if u3 == at:
                s0 = 0.0
            else:
                data3 = graph.get_edge_data(u3, v3, k3)
                geom3 = data3.get("geometry", None)
                s0 = float(geom3.length) if geom3 is not None else 0.0
        coords.append((px, py))
    return coords


__all__ = ["rollout_curv_step_on_graph"]

