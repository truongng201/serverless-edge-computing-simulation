"""
Export a replay dataset of the last N T-Drive trajectories (Phase B) for
use in the TaxiD replay scenario inside serverless-sim.

Usage (from repo root):

    python serverless-sim/scripts/export_taxid_replay_last1k.py \
        --phaseb-dir predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_5k_fast \
        --out-path serverless-sim/mock_data/taxid_replay_last1k.pkl \
        --num-trips 1000

The output is a pickled list of trajectories. Each element is:

    {
        "trip_id": "<id>",
        "points": [
            {"ts": "<iso8601>", "x_m": float, "y_m": float},
            ...
        ],
    }

Coordinates are in meters (same CRS as Phase B: UTM Zone 50N). The
controller that replays this dataset is responsible for converting
meters to pixels using the same transform as StartTaxiDSampleController.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def infer_default_paths() -> Dict[str, Path]:
    """
    Infer default Phase B artifact directory and output path based on
    repo layout, assuming this script lives under serverless-sim/scripts.
    """
    this_file = Path(__file__).resolve()
    repo_root = this_file.parent.parent.parent
    phaseb_dir = (
        repo_root
        / "predict-model-with-taxi"
        / "tdrive_predictor_artifacts"
        / "phase_b_5k_fast"
    )
    out_path = repo_root / "serverless-sim" / "mock_data" / "taxid_replay_last1k.pkl"
    return {"phaseb_dir": phaseb_dir, "out_path": out_path}


def build_argparser() -> argparse.ArgumentParser:
    defaults = infer_default_paths()
    p = argparse.ArgumentParser(
        description="Export last N Phase B trajectories for TaxiD replay."
    )
    p.add_argument(
        "--phaseb-dir",
        type=str,
        default=str(defaults["phaseb_dir"]),
        help="Path to Phase B artifact directory (must contain test.pkl).",
    )
    p.add_argument(
        "--out-path",
        type=str,
        default=str(defaults["out_path"]),
        help="Output pickle path for replay trajectories.",
    )
    p.add_argument(
        "--num-trips",
        type=int,
        default=1000,
        help="Number of last trajectories (by trip_id) to export.",
    )
    return p


def export_replay(
    phaseb_dir: Path,
    out_path: Path,
    num_trips: int = 1000,
) -> None:
    test_path = phaseb_dir / "test.pkl"
    if not test_path.exists():
        raise FileNotFoundError(f"test.pkl not found at {test_path}")

    print(f"[ReplayExport] Loading test set from: {test_path}")
    test_df = pd.read_pickle(test_path)
    if "trip_id" not in test_df.columns or "x" not in test_df.columns or "y" not in test_df.columns:
        raise ValueError("test.pkl must contain 'trip_id','x','y' columns")

    # Ensure deterministic ordering
    test_df = test_df.sort_values(["trip_id", "ts"]).reset_index(drop=True)
    trip_ids = sorted(test_df["trip_id"].unique().tolist())
    if not trip_ids:
        raise ValueError("No trip_id found in test set")

    if num_trips > len(trip_ids):
        num_trips = len(trip_ids)

    keep_ids = trip_ids[-num_trips:]
    print(f"[ReplayExport] Total trips={len(trip_ids)} | exporting last={len(keep_ids)}")

    trajectories: List[Dict[str, Any]] = []
    for tid in keep_ids:
        g = test_df[test_df["trip_id"] == tid].sort_values("ts")
        points = []
        for _, row in g.iterrows():
            ts = row["ts"]
            # Serialize timestamp as ISO string for readability; controller can parse back if needed.
            ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            points.append(
                {
                    "ts": ts_iso,
                    "x_m": float(row["x"]),
                    "y_m": float(row["y"]),
                }
            )
        trajectories.append({"trip_id": str(tid), "points": points})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(trajectories, out_path)
    total_points = sum(len(t["points"]) for t in trajectories)
    print(
        f"[ReplayExport] Saved {len(trajectories)} trajectories | total points={total_points} -> {out_path}"
    )


def main() -> None:
    parser = build_argparser()
    args = parser.parse_args()
    export_replay(
        phaseb_dir=Path(args.phaseb_dir),
        out_path=Path(args.out_path),
        num_trips=int(args.num_trips),
    )


if __name__ == "__main__":
    main()

