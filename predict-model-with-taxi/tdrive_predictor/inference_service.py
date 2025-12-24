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

import os
import numpy as np
import pandas as pd
import torch

from .model import (
    GRUDisplacement,
    GRUDisplacementRoad,
    GRUStepDecoderRoad,
)
from .road_rollout import rollout_curv_step_on_graph
from .osm.loader import load_graph
from .mapmatch.hmm import CandidateGenerator

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
    graph: Optional[object] = None
    cand: Optional[CandidateGenerator] = None

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
    # Optional: load road graph for Phase B curv_step inference if configured.
    graph = None
    cand = None
    if mode == "curv_step" and meta.get("phase", "A") == "B":
        graphml_path = os.environ.get("TDRIVE_GRAPHML_PATH")
        if graphml_path:
            try:
                graph = load_graph(graphml_path=graphml_path, place=None, bbox=None, project=True)
                cand = CandidateGenerator(graph)
                print(f"[Inference] Loaded road graph from {graphml_path} for curv_step rollout.", flush=True)
            except Exception as exc:
                print(f"[Inference] Failed to load graph from {graphml_path}: {exc}", flush=True)
                graph = None
                cand = None
    bundle = PredictorBundle(
        model=model,
        device=torch.device(device),
        feature_cols=feature_cols,
        lookback=lookback,
        mode=mode,
        scaler=scaler,
        graph=graph,
        cand=cand,
    )
    return bundle.to(bundle.device)


def _apply_scaler(df: pd.DataFrame, scaler: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    df = df.copy()
    for col, (mu, sigma) in scaler.items():
        if col in df.columns:
            scale = sigma if sigma else 1.0
            df[col] = (df[col] - mu) / scale
    return df


def _ensure_feature_cols(df: pd.DataFrame, feature_cols: Sequence[str]) -> pd.DataFrame:
    """Ensure all requested feature columns exist in df.

    Serverless-sim histories may not contain optional features (e.g., graph context),
    but the model expects the full training-time feature set. Missing columns are
    filled with 0.0 (in *raw* space, before scaling).
    """
    df = df.copy()
    missing = [c for c in feature_cols if c not in df.columns]
    for c in missing:
        df[c] = 0.0
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
    df = _ensure_feature_cols(df, bundle.feature_cols)
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
    # Prefer graph-constrained rollout when a road graph is available; otherwise
    # fall back to simple heading-based propagation.
    graph = getattr(bundle, "graph", None)
    cand = getattr(bundle, "cand", None)
    x0, y0 = base_pos
    if graph is not None and cand is not None:
        cur_edge = None
        cur_s = None
        # If caller provided edge/s in the last history record, reuse them
        last = history[-1]
        if "edge" in last:
            cur_edge = last["edge"]
            cur_s = last.get("s", None)
        # Otherwise, project base position to nearest edge
        if (cur_edge is None) or (cur_s is None):
            try:
                cands0 = cand.query(float(x0), float(y0))
            except Exception:
                cands0 = []
            if cands0:
                cur_edge = cands0[0]["edge"]
                cur_s = cands0[0]["s"]
        if cur_edge is not None and cur_s is not None and np.isfinite(cur_s):
            xy_steps = rollout_curv_step_on_graph(
                graph,
                cand,
                cur_edge,
                float(cur_s),
                ds_seq,
                x0,
                y0,
            )
            coords: List[Tuple[int, float, float]] = []
            for step_idx, (px, py) in enumerate(xy_steps, start=1):
                if step_idx in horizons:
                    coords.append((step_idx, px, py))
            return coords
    # Fallback: free-space rollout using last heading
    dir_vec = _heading_vector(history)
    coords_fallback: List[Tuple[int, float, float]] = []
    px, py = x0, y0
    for step, ds in enumerate(ds_seq, start=1):
        px += dir_vec[0] * float(ds)
        py += dir_vec[1] * float(ds)
        if step in horizons:
            coords_fallback.append((step, px, py))
    return coords_fallback


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


# ============================================================================
# BATCH INFERENCE FUNCTIONS (for performance with many users)
# ============================================================================

def prepare_batch_from_histories(
    histories: Sequence[Sequence[HistoryRecord]],
    bundle: PredictorBundle,
) -> Tuple[torch.Tensor, List[Tuple[float, float]], List[np.ndarray]]:
    """Convert multiple user histories into a batched tensor [N, L, F].
    
    Returns:
        x_batch: Tensor of shape [N, L, F] with normalized features
        base_positions: List of (x, y) tuples for each user's last position
        heading_vectors: List of heading unit vectors for each user
    """
    batch_seqs = []
    base_positions = []
    heading_vectors = []
    
    for history in histories:
        if len(history) < bundle.lookback:
            raise ValueError(
                f"Need at least {bundle.lookback} history points, got {len(history)}"
            )
        df = pd.DataFrame(list(history)).sort_values("ts")
        df = df.tail(bundle.lookback)
        df = _ensure_feature_cols(df, bundle.feature_cols)
        df = _apply_scaler(df, bundle.scaler)
        x_seq = torch.tensor(df[bundle.feature_cols].to_numpy(dtype=np.float32))
        batch_seqs.append(x_seq)
        
        base_x = float(df["x"].iloc[-1])
        base_y = float(df["y"].iloc[-1])
        base_positions.append((base_x, base_y))
        heading_vectors.append(_heading_vector(history))
    
    # Stack all sequences into batch tensor [N, L, F]
    x_batch = torch.stack(batch_seqs, dim=0).to(bundle.device)
    return x_batch, base_positions, heading_vectors


def predict_future_positions_batch(
    bundle: PredictorBundle,
    histories: Sequence[Sequence[HistoryRecord]],
    horizons: Sequence[int] = (1, 3, 5, 10),
) -> List[List[Tuple[int, float, float]]]:
    """Batch prediction for multiple users. Returns list of coordinate lists.
    
    This is much more efficient than calling predict_future_positions N times
    because it runs a single forward pass through the model.
    """
    if not histories:
        return []
    
    x_batch, base_positions, heading_vectors = prepare_batch_from_histories(histories, bundle)
    
    if bundle.mode != "curv_step":
        raise NotImplementedError("Only curv_step models are supported in batch inference")
    
    # Single forward pass for all users
    with torch.no_grad():
        pred = bundle.model(x_batch, teacher=None, ss_prob=1.0)  # [N, max_steps]
    
    ds_batch = pred.cpu().numpy().astype(np.float32)  # [N, max_steps]
    
    # Process each user's predictions
    results = []
    for i, (base_pos, dir_vec, ds_seq) in enumerate(zip(base_positions, heading_vectors, ds_batch)):
        x0, y0 = base_pos
        
        # For simplicity, use heading-based rollout (no graph constraint in batch mode)
        # Graph-based rollout would require sequential processing anyway
        coords = []
        px, py = x0, y0
        for step, ds in enumerate(ds_seq, start=1):
            px += dir_vec[0] * float(ds)
            py += dir_vec[1] * float(ds)
            if step in horizons:
                coords.append((step, px, py))
        results.append(coords)
    
    return results


def cloudlet_probabilities_batch(
    predicted_coords_batch: Sequence[Sequence[Tuple[int, float, float]]],
    cloudlets: Sequence[CloudletRecord],
    temperature: float = 50.0,
    max_radius: Optional[float] = None,
) -> List[np.ndarray]:
    """Compute cloudlet probabilities for a batch of users.
    
    Returns list of probability arrays, one per user.
    """
    if not cloudlets:
        raise ValueError("cloudlets list cannot be empty")
    
    cloud_xy = np.array([(c["x"], c["y"]) for c in cloudlets], dtype=np.float32)
    results = []
    
    for predicted_coords in predicted_coords_batch:
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
        results.append(np.stack(probs, axis=-1) if probs else np.array([]))
    
    return results


__all__ = [
    "PredictorBundle",
    "load_predictor_bundle",
    "prepare_sequence_from_history",
    "predict_future_positions",
    "cloudlet_probabilities",
    # Batch inference functions
    "prepare_batch_from_histories",
    "predict_future_positions_batch",
    "cloudlet_probabilities_batch",
]
