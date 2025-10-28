"""
HMM map-matching (initial implementation) for Phase B.

Implements:
  - Candidate generation via STRtree over edge geometries (projected CRS)
  - Emission log-probabilities: Gaussian on perpendicular distance to edge
  - Transition log-probabilities: based on path length feasibility vs dt/vmax,
    with an option to approximate by Euclidean distance between footpoints
  - Viterbi decoding per trip with simple pruning and free-space fallback
"""

from typing import List, Tuple, Optional, Any, Dict

import math

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None

try:
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
except Exception as e:  # pragma: no cover
    raise ImportError("shapely is required for HMM map-matching. Install with `pip install shapely`. ")


class CandidateGenerator:
    """Generate road-segment candidates using a spatial index over edge geometries.

    The graph must be projected (meters). For each edge, we obtain a LineString
    geometry; if missing, we create one from node coordinates. We then build an
    STRtree for fast spatial querying.
    """

    def __init__(self, graph: Any, radius_m: float = 50.0, k: int = 5):
        self.graph = graph
        self.radius_m = float(radius_m)
        self.k = int(k)
        geoms: List[LineString] = []
        edge_keys: List[Tuple[int, int, int]] = []
        edge_len: List[float] = []
        # build shapely geometries for edges
        for u, v, key, data in graph.edges(keys=True, data=True):
            geom = data.get('geometry', None)
            if geom is None:
                # fall back to straight line between nodes
                ux = graph.nodes[u].get('x')
                uy = graph.nodes[u].get('y')
                vx = graph.nodes[v].get('x')
                vy = graph.nodes[v].get('y')
                if ux is None or uy is None or vx is None or vy is None:
                    continue
                geom = LineString([(ux, uy), (vx, vy)])
            geoms.append(geom)
            edge_keys.append((u, v, key))
            edge_len.append(float(geom.length))
        if not geoms:
            raise ValueError("Graph has no edges with usable geometry.")
        self._tree = STRtree(geoms)
        # mapping: geom -> index
        self._geom_to_idx = {id(g): i for i, g in enumerate(geoms)}
        self._edges = edge_keys
        self._edge_len = edge_len
        self._geoms = geoms

    def query(self, x: float, y: float) -> List[Dict[str, Any]]:
        """Return up to K candidates: dicts with edge, dist, s, foot (x,y).

        We first get rough candidates by querying the bounding box of a radius
        buffer, then compute exact distances and return the best K within radius.
        """
        p = Point(float(x), float(y))
        env = p.buffer(self.radius_m).envelope
        rough = self._tree.query(env)
        cands: List[Tuple[float, int]] = []  # (distance, idx)
        for geom in rough:
            idx = self._geom_to_idx.get(id(geom))
            if idx is None:
                continue
            d = geom.distance(p)
            if d <= self.radius_m:
                cands.append((d, idx))
        if not cands:
            return []
        cands.sort(key=lambda t: t[0])
        # deduplicate by edge, take top K
        out: List[Dict[str, Any]] = []
        seen = set()
        for d, idx in cands:
            edge = self._edges[idx]
            if edge in seen:
                continue
            seen.add(edge)
            geom = self._geoms[idx]
            s = geom.project(p)
            foot = geom.interpolate(s)
            out.append({
                'edge': edge,
                'dist': float(d),
                's': float(s),
                'edge_len': float(self._edge_len[idx]),
                'foot_xy': (float(foot.x), float(foot.y)),
            })
            if len(out) >= self.k:
                break
        return out

    def edge_endpoints(self, edge: Tuple[int, int, int]) -> Tuple[int, int]:
        return (edge[0], edge[1])


class HMMMapMatcher:
    """Hidden Markov Model map-matcher with Viterbi decoding (initial version)."""

    def __init__(self, graph: Any, cand_gen: CandidateGenerator, sigma_gps: float = 10.0,
                 max_speed_kmh: float = 160.0, speed_scale_mps: float = 20.0,
                 use_shortest_path: bool = False):
        self.graph = graph
        self.cand_gen = cand_gen
        self.sigma_gps = float(sigma_gps)
        self.max_speed_mps = float(max_speed_kmh) / 3.6
        self.speed_scale_mps = float(speed_scale_mps)
        self.use_shortest_path = bool(use_shortest_path)

    def _emission_logp(self, d: float) -> float:
        return - (d * d) / (2.0 * self.sigma_gps * self.sigma_gps + 1e-9)

    def _path_length(self, prev: Dict[str, Any], curr: Dict[str, Any]) -> float:
        # Same edge: along-edge distance
        if prev['edge'] == curr['edge']:
            return abs(curr['s'] - prev['s'])
        if not self.use_shortest_path or nx is None:
            # Fallback: Euclidean between footpoints
            (x1, y1) = prev['foot_xy']
            (x2, y2) = curr['foot_xy']
            return math.hypot(x2 - x1, y2 - y1)
        # With shortest-path over graph + along-edge tails
        ui, vi = self.cand_gen.edge_endpoints(prev['edge'])
        uj, vj = self.cand_gen.edge_endpoints(curr['edge'])
        li = float(prev['edge_len'])
        lj = float(curr['edge_len'])
        si = float(prev['s'])
        sj = float(curr['s'])
        tails = [
            (si, ui),  # prev to ui
            (li - si, vi),  # prev to vi
        ]
        heads = [
            (sj, uj),  # from uj to curr
            (lj - sj, vj),  # from vj to curr
        ]
        best = float('inf')
        for di, ni in tails:
            for dj, nj in heads:
                try:
                    sp = nx.shortest_path_length(self.graph, ni, nj, weight='length')
                except Exception:
                    sp = float('inf')
                total = di + sp + dj
                if total < best:
                    best = total
        return best

    def match_trip(self, xs: List[float], ys: List[float], ts: List[Any]) -> List[Optional[Dict[str, Any]]]:
        """Return matched candidate per observation (dict with edge, s, foot_xy, etc.).

        If no candidates at a time-step, returns None for that step.
        """
        T = len(xs)
        cand_list: List[List[Dict[str, Any]]] = []
        for i in range(T):
            cands = self.cand_gen.query(xs[i], ys[i])
            cand_list.append(cands)
        if not any(cand_list):
            return [None] * T
        # Viterbi DP arrays
        dp: List[List[float]] = []
        back: List[List[Optional[int]]] = []
        for t in range(T):
            cands = cand_list[t]
            Kt = len(cands)
            if Kt == 0:
                dp.append([])
                back.append([])
                continue
            dp.append([float('-inf')] * Kt)
            back.append([None] * Kt)
            # emission
            em = [self._emission_logp(c['dist']) for c in cands]
            if t == 0:
                for k in range(Kt):
                    dp[t][k] = em[k]
            else:
                prev_cands = cand_list[t - 1]
                Kp = len(prev_cands)
                if Kp == 0:
                    for k in range(Kt):
                        dp[t][k] = em[k]
                else:
                    dt = (ts[t] - ts[t - 1]).total_seconds() if hasattr(ts[t], 'to_pydatetime') or hasattr(ts[t], 'timestamp') else float(ts[t] - ts[t - 1]).total_seconds()
                    if not isinstance(dt, float):
                        try:
                            dt = float(dt)
                        except Exception:
                            dt = 60.0
                    for k in range(Kt):
                        best = float('-inf')
                        best_i = None
                        for i in range(Kp):
                            L = self._path_length(prev_cands[i], cands[k])
                            if not math.isfinite(L):
                                continue
                            if L > self.max_speed_mps * max(1.0, dt) * 1.5:  # feasibility with margin
                                continue
                            log_trans = - L / (self.speed_scale_mps * max(1.0, dt))
                            score = dp[t - 1][i] + log_trans + em[k]
                            if score > best:
                                best = score
                                best_i = i
                        if best_i is not None:
                            dp[t][k] = best
                            back[t][k] = best_i
                        else:
                            dp[t][k] = em[k]
                            back[t][k] = None
        # Backtrack: choose best candidate at final time with any candidates
        matched: List[Optional[Dict[str, Any]]] = [None] * T
        # find last t with candidates
        last_t = None
        for t in range(T - 1, -1, -1):
            if len(cand_list[t]) > 0:
                last_t = t
                break
        if last_t is None:
            return matched
        last_scores = dp[last_t]
        if not last_scores:
            return matched
        k_star = max(range(len(last_scores)), key=lambda k: last_scores[k])
        t = last_t
        while t >= 0:
            cands = cand_list[t]
            if not cands:
                t -= 1
                continue
            matched[t] = cands[k_star]
            prev = back[t][k_star]
            if prev is None:
                # stop backtracking at this gap
                t -= 1
                # choose next best at previous t if exists
                if t >= 0 and len(cand_list[t]) > 0:
                    k_star = max(range(len(dp[t])), key=lambda k: dp[t][k])
                continue
            k_star = prev
            t -= 1
        return matched
