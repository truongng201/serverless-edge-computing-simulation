"""Offline forecast evaluation for the paper's forecast-accuracy table.

Evaluates, on the Phase B test split, the forecasters that drive prewarming in
the simulator:
  - gru_heading : the GRU checkpoint through the SAME batched inference path the
                  simulator uses (displacements rolled out along the last heading)
  - cv          : constant velocity, mean velocity of the last 3 steps
  - persistence : the user does not move

For each forecaster it reports, per horizon h in {1,3,5,10} minutes, the mean
Euclidean error (m) and Hit@200 (%), and at h=5 the cloudlet accuracy: the share
of forecasts whose nearest cloudlet equals the cloudlet nearest to the true
position, for the simulator's grid placement with E cloudlets. It also reports
how often the true nearest cloudlet at t+5 differs from the one at t (how often
a forecast could matter at all).

Only windows with L observations and a full 10-step future are used, which
matches the predictor's own evaluation protocol.

Usage (server, from serverless-sim/):
  python scripts/eval_forecasters.py \
      --phaseb-dir ../predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_7k_fast \
      --ckpt gru_phase_curv_step.pt --edges 10 50 100 --max-samples 200000

Without torch, add --no-gru (CV and persistence only). Cloudlet positions need
the map bounds: by default they come from the OSM graph exactly as in the
simulator's dataset setup; pass --bounds MINX MINY MAXX MAXY to skip osmnx.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))
sys.path.insert(0, str(SIM_ROOT.parent / "predict-model-with-taxi"))

from config import Config  # noqa: E402

HORIZONS = (1, 3, 5, 10)
HIT_RADIUS_M = 200.0


def map_bounds(args) -> Tuple[float, float, float, float]:
    if args.bounds:
        return tuple(args.bounds)  # type: ignore[return-value]
    from central_node.control_layer.helper_module.osm_loader import graph_bounds_meters, load_graph

    graph = load_graph(xml_path=Config.TAXID_OSM_XML_PATH, graphml_path=Config.TAXID_GRAPHML_PATH, project=True)
    return graph_bounds_meters(graph)


def cloudlet_positions_m(n_edges: int, bounds: Tuple[float, float, float, float]) -> np.ndarray:
    """Cloudlet positions (UTM meters) exactly as the simulator places them."""
    from central_node.control_layer.controller_module.register_edge_node_controller import (
        RegisterEdgeNodeController,
    )

    minx, miny, maxx, maxy = bounds
    px_per_m = 1.0 / Config.DEFAULT_PIXEL_TO_METERS

    class _Sched:  # SetDatasetController re-centers the central node on the map bbox
        central_node = {"location": {"x": (maxx - minx) / 2 * px_per_m, "y": (maxy - miny) / 2 * px_per_m}}

    placer = RegisterEdgeNodeController.__new__(RegisterEdgeNodeController)
    placer.scheduler = _Sched()
    pos = []
    for i in range(n_edges):
        loc = RegisterEdgeNodeController._grid_based_location(placer, f"edge_{i + 1:03d}", total_nodes=n_edges)
        # Simulator pixel frame -> UTM: x_px = (x - minx)/10, y_px = (maxy - y)/10
        pos.append((minx + loc["x"] * Config.DEFAULT_PIXEL_TO_METERS, maxy - loc["y"] * Config.DEFAULT_PIXEL_TO_METERS))
    return np.asarray(pos, dtype=np.float64)


def nearest(points: np.ndarray, cloudlets: np.ndarray) -> np.ndarray:
    d2 = ((points[:, None, :] - cloudlets[None, :, :]) ** 2).sum(axis=2)
    return d2.argmin(axis=1)


def build_windows(test: pd.DataFrame, lookback: int, max_samples: int, seed: int):
    """Return (trip groups, list of (trip_key, end_index)) for windows with a full future."""
    groups = {k: g.sort_values("ts").reset_index(drop=True) for k, g in test.groupby("trip_id")}
    windows = []
    for k, g in groups.items():
        for i in range(lookback - 1, len(g) - max(HORIZONS)):
            windows.append((k, i))
    if max_samples and len(windows) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(windows), size=max_samples, replace=False)
        windows = [windows[j] for j in sorted(idx)]
    return groups, windows


def gru_heading_forecasts(args, groups, windows, raw: Dict[str, pd.DataFrame]) -> np.ndarray:
    from tdrive_predictor.inference_service import load_predictor_bundle, predict_future_positions_batch

    bundle = load_predictor_bundle(Path(args.phaseb_dir), args.ckpt, args.device)
    out = np.zeros((len(windows), len(HORIZONS), 2))
    batch: List[List[dict]] = []
    slots: List[int] = []

    def flush():
        coords = predict_future_positions_batch(bundle, batch)
        for slot, cs in zip(slots, coords):
            by_h = {h: (x, y) for h, x, y in cs}
            out[slot] = [by_h[h] for h in HORIZONS]
        batch.clear()
        slots.clear()

    for n, (k, i) in enumerate(windows):
        g = raw[k]
        win = g.iloc[i - bundle.lookback + 1: i + 1]
        batch.append(win.to_dict("records"))
        slots.append(n)
        if len(batch) >= args.batch_size:
            flush()
    if batch:
        flush()
    return out


def summarize(name: str, pred: np.ndarray, true: np.ndarray, now: np.ndarray, cloudlet_sets) -> dict:
    err = np.linalg.norm(pred - true, axis=2)  # [N, 4]
    row = {"forecaster": name, "n": len(pred)}
    for j, h in enumerate(HORIZONS):
        row[f"err_h{h}_m"] = float(err[:, j].mean())
        row[f"hit200_h{h}_pct"] = float((err[:, j] <= HIT_RADIUS_M).mean() * 100)
    j5 = HORIZONS.index(5)
    for e, cl in cloudlet_sets.items():
        true_c = nearest(true[:, j5], cl)
        row[f"cloudlet_acc_E{e}_pct"] = float((nearest(pred[:, j5], cl) == true_c).mean() * 100)
        row[f"true_move_E{e}_pct"] = float((nearest(now, cl) != true_c).mean() * 100)
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phaseb-dir", required=True)
    ap.add_argument("--ckpt", default="gru_phase_curv_step.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--edges", type=int, nargs="+", default=[10, 50, 100])
    ap.add_argument("--max-samples", type=int, default=200000)
    ap.add_argument("--batch-size", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-gru", action="store_true")
    ap.add_argument("--bounds", type=float, nargs=4, metavar=("MINX", "MINY", "MAXX", "MAXY"))
    ap.add_argument("--out", default="forecast_accuracy.csv")
    args = ap.parse_args()

    phaseb = Path(args.phaseb_dir)
    test = pd.read_pickle(phaseb / "test.pkl")
    scaler = pd.read_pickle(phaseb / "scaler.pkl")
    groups, windows = build_windows(test, args.lookback, args.max_samples, args.seed)
    print(f"[eval] {len(groups)} trips, {len(windows)} windows")

    # test.pkl features are standardized; the inference path expects raw values.
    raw = {}
    for k, g in groups.items():
        g = g.copy()
        for col, (mu, sigma) in scaler.items():
            if col in g.columns:
                g[col] = g[col] * (sigma if sigma else 1.0) + mu
        g["ts"] = (g["ts"] - g["ts"].iloc[0]).dt.total_seconds()
        raw[k] = g

    now = np.array([[groups[k].at[i, "x"], groups[k].at[i, "y"]] for k, i in windows])
    prev3 = np.array([[groups[k].at[i - 3, "x"], groups[k].at[i - 3, "y"]] for k, i in windows])
    true = np.array([[[groups[k].at[i + h, "x"], groups[k].at[i + h, "y"]] for h in HORIZONS] for k, i in windows])

    hs = np.asarray(HORIZONS, dtype=np.float64)[None, :, None]
    forecasts = {
        "persistence": np.repeat(now[:, None, :], len(HORIZONS), axis=1),
        "cv": now[:, None, :] + hs * ((now - prev3) / 3.0)[:, None, :],
    }
    if not args.no_gru:
        forecasts["gru_heading"] = gru_heading_forecasts(args, groups, windows, raw)

    bounds = map_bounds(args)
    cloudlet_sets = {e: cloudlet_positions_m(e, bounds) for e in args.edges}
    rows = [summarize(name, pred, true, now, cloudlet_sets) for name, pred in forecasts.items()]
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.T.to_string(header=False))
    df.to_csv(args.out, index=False)
    print(f"[eval] wrote {args.out}")


if __name__ == "__main__":
    main()
