"""
Export a replay dataset of T-Drive trajectories (Phase B) for use in the
TaxiD replay scenario inside serverless-sim.

Usage (from repo root):

    # Export 1000 trajectories (default)
    python serverless-sim/scripts/export_taxid_replay_last1k.py

    # Export all trajectories
    python serverless-sim/scripts/export_taxid_replay_last1k.py --num-trips all

    # Export specific number
    python serverless-sim/scripts/export_taxid_replay_last1k.py --num-trips 5000

    # Export with full features (for predictive model)
    python serverless-sim/scripts/export_taxid_replay_last1k.py --include-features

The output is a pickled list of trajectories. Each element is:

    {
        "trip_id": "<id>",
        "points": [
            {
                "ts": "<iso8601>",
                "x_m": float,
                "y_m": float,
                # If --include-features:
                "v": float,           # velocity (m/s)
                "a": float,           # acceleration (m/s^2)
                "delta_v": float,     # velocity change
                "delta_heading": float,
                "tod_sin": float,     # time of day (sin)
                "tod_cos": float,     # time of day (cos)
                "dow_sin": float,     # day of week (sin)
                "dow_cos": float,     # day of week (cos)
                "rush_hour": float,   # rush hour flag
                "stop_flag": float,   # stopped flag
                "dw_time": float,     # dwell time (seconds)
            },
            ...
        ],
    }

Coordinates are in meters (same CRS as Phase B: UTM Zone 50N / EPSG:32650).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# Feature columns that can be exported from test.pkl
FEATURE_COLS = [
    "v", "a", "delta_v", "delta_heading",
    "tod_sin", "tod_cos", "dow_sin", "dow_cos",
    "rush_hour", "stop_flag", "dw_time"
]


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
    out_path = repo_root / "serverless-sim" / "mock_data" / "taxid_replay.pkl"
    return {"phaseb_dir": phaseb_dir, "out_path": out_path}


def build_argparser() -> argparse.ArgumentParser:
    defaults = infer_default_paths()
    p = argparse.ArgumentParser(
        description="Export Phase B trajectories for TaxiD replay simulation."
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
        default=None,
        help="Output pickle path. Default: auto-generate based on num-trips.",
    )
    p.add_argument(
        "--num-trips",
        type=str,
        default="1000",
        help="Number of trajectories to export. Use 'all' for all trips, or a number.",
    )
    p.add_argument(
        "--include-features",
        action="store_true",
        help="Include pre-computed features (v, a, delta_v, etc.) in output.",
    )
    p.add_argument(
        "--selection",
        type=str,
        choices=["first", "last", "random"],
        default="first",
        help="How to select trips: 'first' N, 'last' N, or 'random' N.",
    )
    return p


def export_replay(
    phaseb_dir: Path,
    out_path: Optional[Path],
    num_trips: str = "1000",
    include_features: bool = False,
    selection: str = "first",
) -> None:
    test_path = phaseb_dir / "test.pkl"
    if not test_path.exists():
        raise FileNotFoundError(f"test.pkl not found at {test_path}")

    print(f"[ReplayExport] Loading test set from: {test_path}")
    test_df = pd.read_pickle(test_path)
    
    required_cols = ["trip_id", "x", "y", "ts"]
    for col in required_cols:
        if col not in test_df.columns:
            raise ValueError(f"test.pkl must contain '{col}' column")

    # Ensure deterministic ordering
    test_df = test_df.sort_values(["trip_id", "ts"]).reset_index(drop=True)
    trip_ids = sorted(test_df["trip_id"].unique().tolist())
    total_trips = len(trip_ids)
    
    if not trip_ids:
        raise ValueError("No trip_id found in test set")

    # Determine how many trips to export
    if num_trips.lower() == "all":
        export_count = total_trips
    else:
        export_count = min(int(num_trips), total_trips)

    # Select trips based on selection method
    if selection == "first":
        keep_ids = trip_ids[:export_count]
    elif selection == "last":
        keep_ids = trip_ids[-export_count:]
    else:  # random
        import random
        random.seed(42)  # Reproducible
        keep_ids = random.sample(trip_ids, export_count)
        keep_ids = sorted(keep_ids)

    print(f"[ReplayExport] Total trips={total_trips} | exporting {selection} {len(keep_ids)}")
    print(f"[ReplayExport] Include features: {include_features}")

    # Determine which feature columns are available
    available_features = [c for c in FEATURE_COLS if c in test_df.columns]
    if include_features:
        print(f"[ReplayExport] Available features: {available_features}")

    # Export trajectories
    trajectories: List[Dict[str, Any]] = []
    
    try:
        from tqdm import tqdm
        trip_iter = tqdm(keep_ids, desc="Exporting trips", unit="trip")
    except ImportError:
        trip_iter = keep_ids
        print("[ReplayExport] Install tqdm for progress bar: pip install tqdm")

    for tid in trip_iter:
        g = test_df[test_df["trip_id"] == tid].sort_values("ts")
        points = []
        for _, row in g.iterrows():
            ts = row["ts"]
            ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            
            point = {
                "ts": ts_iso,
                "x_m": float(row["x"]),
                "y_m": float(row["y"]),
            }
            
            # Add features if requested
            if include_features:
                for feat in available_features:
                    point[feat] = float(row[feat])
            
            points.append(point)
        
        trajectories.append({"trip_id": str(tid), "points": points})

    # Generate output path if not specified
    if out_path is None:
        defaults = infer_default_paths()
        base_dir = defaults["out_path"].parent
        suffix = "_features" if include_features else ""
        if num_trips.lower() == "all":
            filename = f"taxid_replay_all{suffix}.pkl"
        else:
            filename = f"taxid_replay_{export_count}{suffix}.pkl"
        out_path = base_dir / filename

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(trajectories, out_path)
    
    total_points = sum(len(t["points"]) for t in trajectories)
    avg_points = total_points / len(trajectories) if trajectories else 0
    
    print(f"[ReplayExport] Summary:")
    print(f"  Trajectories: {len(trajectories)}")
    print(f"  Total points: {total_points}")
    print(f"  Avg points/trip: {avg_points:.1f}")
    print(f"  Features included: {include_features}")
    print(f"  Output: {out_path}")


def main() -> None:
    parser = build_argparser()
    args = parser.parse_args()
    
    out_path = Path(args.out_path) if args.out_path else None
    
    export_replay(
        phaseb_dir=Path(args.phaseb_dir),
        out_path=out_path,
        num_trips=args.num_trips,
        include_features=args.include_features,
        selection=args.selection,
    )


if __name__ == "__main__":
    main()
