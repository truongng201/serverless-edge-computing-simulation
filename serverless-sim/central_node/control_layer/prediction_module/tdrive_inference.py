"""Bridge between serverless-sim and the T-Drive predictor package."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import sys

import numpy as np

logger = logging.getLogger(__name__)

# Ensure the T-Drive package directory is importable when running from serverless-sim
ROOT_DIR = Path(__file__).resolve().parents[3]
TDRIVE_PKG_DIR = ROOT_DIR / "predict-model-with-taxi"
if TDRIVE_PKG_DIR.exists() and str(TDRIVE_PKG_DIR) not in sys.path:  # pragma: no cover
    sys.path.append(str(TDRIVE_PKG_DIR))

try:
    from tdrive_predictor.inference_service import (
        PredictorBundle,
        cloudlet_probabilities,
        load_predictor_bundle,
        predict_future_positions,
    )
except ImportError as exc:  # pragma: no cover - optional dependency
    PredictorBundle = None  # type: ignore
    load_error = exc
else:
    load_error = None


class TDrivePredictorAdapter:
    """Lazy loader around the predictor bundle."""

    def __init__(
        self,
        artifact_dir: str | Path,
        ckpt_name: Optional[str] = None,
        device: str = "cpu",
        temperature: float = 50.0,
        max_radius: Optional[float] = None,
    ) -> None:
        self.artifact_dir = Path(artifact_dir)
        self.ckpt_name = ckpt_name
        self.device = device
        self.temperature = temperature
        self.max_radius = max_radius
        self.bundle: Optional[PredictorBundle] = None

    def ensure_loaded(self) -> PredictorBundle:
        if load_error is not None:
            raise RuntimeError(
                "tdrive_predictor package is not available in PYTHONPATH"
            ) from load_error
        if self.bundle is None:
            self.bundle = load_predictor_bundle(
                self.artifact_dir, self.ckpt_name, self.device
            )
        return self.bundle

    def predict_user(self, user_state: Dict, cloudlets: Sequence[Dict]) -> np.ndarray:
        bundle = self.ensure_loaded()
        history = user_state.get("history", [])
        if not history:
            raise ValueError("history is required for predictive inference")
        coords = predict_future_positions(bundle, history)
        return cloudlet_probabilities(
            coords,
            cloudlets,
            temperature=self.temperature,
            max_radius=self.max_radius,
        )


def get_mobility_prediction(
    user_states: Sequence[Dict],
    cloudlets: Sequence[Dict],
    adapter: TDrivePredictorAdapter,
) -> Dict[str, np.ndarray]:
    """Return probability tensors for each user."""

    if not user_states:
        return {}
    result = {}
    failed_count = 0
    insufficient_history_count = 0
    
    for user in user_states:
        uid = user.get("user_id")
        if uid is None:
            continue
        try:
            probs = adapter.predict_user(user, cloudlets)
            result[uid] = probs
        except ValueError as e:
            # Usually means insufficient history points
            insufficient_history_count += 1
            logger.debug(f"User {uid} prediction skipped: {e}")
        except Exception as e:
            failed_count += 1
            logger.warning(f"User {uid} prediction failed: {e}")
    
    # Log summary if there were issues
    total_users = len(user_states)
    successful = len(result)
    if insufficient_history_count > 0:
        logger.info(
            f"Predictive assignment: {successful}/{total_users} users predicted, "
            f"{insufficient_history_count} users lack sufficient history (need 20+ points)"
        )
    if failed_count > 0:
        logger.warning(
            f"Predictive assignment: {failed_count} users failed due to errors"
        )
    
    return result
