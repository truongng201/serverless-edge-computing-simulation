"""Lightweight inference utilities for GRU-based T-Drive predictors.

This module exposes helpers to load a trained checkpoint, build the
required tensors from recent user history, run the GRU decoder, and map
predicted waypoints to cloudlet probabilities for consumption by the
serverless scheduler.

Assumptions
-----------
* Metadata (`meta.json`) contains the feature list and default
  lookback. Checkpoints saved by `train.py` also store the `hidden_size`.
* History provided by the caller already contains the feature columns in
  the same order/scale as training (typically after applying the scaler
  shipped with the artifact). Computing raw features from lon/lat is out
  of scope for this helper and should be handled upstream.
* For `curv_step` models we only know the predicted curvilinear distance
  (Δs) for each minute ahead. When no road graph is available we simply
  propagate those distances along the last observed heading. This is
  sufficient for downstream probability scoring against nearby cloudlets.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch

from .model import (
    GRUDisplacement,
    GRUDisplacementRoad,
    GRUStepDecoderRoad,
)

HistoryRecord = Dict[str, float]
CloudletRecord = Dict[str, float]


@dataclass
class PredictorBundle:
    """Container holding all objects needed for inference."""

    model: torch.nn.Module
    device: torch.device
    feature_cols: List[str]
    lookback: int
    mode: str
    scaler: Dict[str, Tuple[float, float]]

    def to(self, device: torch.device) -> "PredictorBundle":
        self.model.to(device)
        self.device = device
        return self


def _build_model(mode: str, input_size: int, hidden_size: int) -> torch.nn.Module:
    if mode == "curv_step":
        return GRUStepDecoderRoad(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            dropout=0.1,
            max_steps=10,
        )
    if mode == "curv":
        return GRUDisplacementRoad(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            dropout=0.1,
        )
    return GRUDisplacement(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=1,
        dropout=0.1,
    )


def load_predictor_bundle(
    artifact_dir: Path | str,
    ckpt_name: Optional[str] = None,
    device: str | torch.device = "cpu",
) -> PredictorBundle:
    """Load model, scaler, and metadata from a training artifact directory."""

    artifact_path = Path(artifact_dir)
    meta = pd.read_json(artifact_path / "meta.json", typ="series").to_dict()
    feature_cols: List[str] = list(meta["feature_cols"])
    lookback = int(meta.get("lookback_default", meta.get("lookback", 20)))
    mode = meta.get("mode", "curv_step")
    ckpt_file = ckpt_name or (
        "gru_phase_curv_step.pt"
        if mode == "curv_step"
        else ("gru_phase_curv.pt" if mode == "curv" else "gru_phase_a.pt")
    )
    ckpt_path = artifact_path / ckpt_file
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location="cpu")
    hidden_size = int(ckpt.get("hidden_size", 256 if mode != "xy" else 128))
    model = _build_model(mode, len(feature_cols), hidden_size)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    scaler = pd.read_pickle(artifact_path / "scaler.pkl")
    bundle = PredictorBundle(
        model=model,
        device=torch.device(device),
        feature_cols=feature_cols,
        lookback=lookback,
        mode=mode,
        scaler=scaler,
    )
    return bundle.to(bundle.device)


def _apply_scaler(df: pd.DataFrame, scaler: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    df = df.copy()
    for col, (mu, sigma) in scaler.items():
        if col in df.columns:
            scale = sigma if sigma else 1.0
            df[col] = (df[col] - mu) / scale
    return df


def prepare_sequence_from_history(
    history: Sequence[HistoryRecord],
    bundle: PredictorBundle,
) -> Tuple[torch.Tensor, Tuple[float, float]]:
    """Convert recent history into a normalized tensor of size [1, L, F]."""

    if len(history) < bundle.lookback:
        raise ValueError(
            f"Need at least {bundle.lookback} history points, got {len(history)}"
        )
    df = pd.DataFrame(list(history)).sort_values("ts")
    df = df.tail(bundle.lookback)
    df = _apply_scaler(df, bundle.scaler)
    x_seq = torch.tensor(df[bundle.feature_cols].to_numpy(dtype=np.float32))
    base_x = float(df["x"].iloc[-1])
    base_y = float(df["y"].iloc[-1])
    return x_seq.unsqueeze(0).to(bundle.device), (base_x, base_y)


def _heading_vector(history: Sequence[HistoryRecord]) -> np.ndarray:
    if len(history) < 2:
        return np.array([1.0, 0.0], dtype=np.float32)
    p1 = history[-2]
    p2 = history[-1]
    dx = float(p2["x"] - p1["x"])
    dy = float(p2["y"] - p1["y"])
    norm = np.hypot(dx, dy)
    if norm < 1e-6:
        return np.array([1.0, 0.0], dtype=np.float32)
    return np.array([dx / norm, dy / norm], dtype=np.float32)


def predict_future_positions(
    bundle: PredictorBundle,
    history: Sequence[HistoryRecord],
    horizons: Sequence[int] = (1, 3, 5, 10),
) -> List[Tuple[int, float, float]]:
    """Return absolute coordinates for the requested horizons."""

    x_seq, base_pos = prepare_sequence_from_history(history, bundle)
    if bundle.mode != "curv_step":
        raise NotImplementedError("Only curv_step models are supported in inference")
    with torch.no_grad():
        pred = bundle.model(x_seq, teacher=None, ss_prob=1.0)
    ds_seq = pred.squeeze(0).cpu().numpy().astype(np.float32)
    dir_vec = _heading_vector(history)
    coords: List[Tuple[int, float, float]] = []
    px, py = base_pos
    for step, ds in enumerate(ds_seq, start=1):
        px += dir_vec[0] * float(ds)
        py += dir_vec[1] * float(ds)
        if step in horizons:
            coords.append((step, px, py))
    return coords


def cloudlet_probabilities(
    predicted_coords: Sequence[Tuple[int, float, float]],
    cloudlets: Sequence[CloudletRecord],
    temperature: float = 50.0,
    max_radius: Optional[float] = None,
) -> np.ndarray:
    """Compute softmax probabilities over cloudlets for each horizon."""

    if not cloudlets:
        raise ValueError("cloudlets list cannot be empty")
    cloud_xy = np.array([(c["x"], c["y"]) for c in cloudlets], dtype=np.float32)
    probs: List[np.ndarray] = []
    for _, px, py in predicted_coords:
        d = np.linalg.norm(cloud_xy - np.array([px, py]), axis=1)
        if max_radius is not None:
            mask = d <= max_radius
            if not np.any(mask):
                mask = np.ones_like(d, dtype=bool)
            d = np.where(mask, d, np.max(d[mask]) + 1e6)
        score = -d / max(temperature, 1.0)
        score -= score.max()
        exp_score = np.exp(score)
        probs.append(exp_score / exp_score.sum())
    return np.stack(probs, axis=-1)


__all__ = [
    "PredictorBundle",
    "load_predictor_bundle",
    "prepare_sequence_from_history",
    "predict_future_positions",
    "cloudlet_probabilities",
]

