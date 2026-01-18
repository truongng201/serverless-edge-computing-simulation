"""Bridge between serverless-sim and the T-Drive predictor package."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import sys

import numpy as np

logger = logging.getLogger(__name__)

# Ensure the T-Drive package directory is importable when running from serverless-sim
# Path: serverless-sim/central_node/control_layer/prediction_module/tdrive_inference.py
# parents[0]=prediction_module, [1]=control_layer, [2]=central_node, [3]=serverless-sim, [4]=project_root
ROOT_DIR = Path(__file__).resolve().parents[4]
TDRIVE_PKG_DIR = ROOT_DIR / "predict-model-with-taxi"

logger.info(f"TDrive package directory: {TDRIVE_PKG_DIR}")

if TDRIVE_PKG_DIR.exists() and str(TDRIVE_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(TDRIVE_PKG_DIR))  # Insert at beginning for priority
    logger.info(f"Added {TDRIVE_PKG_DIR} to sys.path")

try:
    from tdrive_predictor.inference_service import (
        PredictorBundle,
        cloudlet_probabilities,
        load_predictor_bundle,
        predict_future_positions,
        # Batch inference functions for performance
        predict_future_positions_batch,
        cloudlet_probabilities_batch,
    )
    load_error = None
    BATCH_INFERENCE_AVAILABLE = True
    logger.info("Successfully imported tdrive_predictor.inference_service (with batch support)")
except ImportError as exc:  # pragma: no cover - optional dependency
    PredictorBundle = None  # type: ignore
    load_error = exc
    BATCH_INFERENCE_AVAILABLE = False
    logger.error(f"Failed to import tdrive_predictor: {exc}")
    logger.error(f"TDRIVE_PKG_DIR exists: {TDRIVE_PKG_DIR.exists()}")
    logger.error(f"sys.path includes: {[p for p in sys.path if 'predict' in p.lower()]}")


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
        """Single user prediction (legacy, use predict_users_batch for better performance)."""
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
    
    def predict_users_batch(
        self, user_states: Sequence[Dict], cloudlets: Sequence[Dict]
    ) -> Dict[str, np.ndarray]:
        """Batch prediction for multiple users - much more efficient than sequential calls.
        
        Runs a single forward pass through the model for all users.
        """
        if not user_states:
            return {}
        
        bundle = self.ensure_loaded()
        
        # Filter users with valid history and collect their data
        valid_users = []
        valid_histories = []
        user_ids = []
        
        for user in user_states:
            uid = user.get("user_id")
            history = user.get("history", [])
            if uid is None or len(history) < bundle.lookback:
                continue
            valid_users.append(user)
            valid_histories.append(history)
            user_ids.append(uid)
        
        if not valid_histories:
            return {}
        
        # Run batch prediction
        coords_batch = predict_future_positions_batch(bundle, valid_histories)
        probs_batch = cloudlet_probabilities_batch(
            coords_batch,
            cloudlets,
            temperature=self.temperature,
            max_radius=self.max_radius,
        )
        
        # Map results back to user IDs
        return {uid: probs for uid, probs in zip(user_ids, probs_batch)}


def get_mobility_prediction(
    user_states: Sequence[Dict],
    cloudlets: Sequence[Dict],
    adapter: TDrivePredictorAdapter,
) -> Dict[str, np.ndarray]:
    """Return probability tensors for each user.
    
    Uses batch inference when available for better performance with many users.
    Falls back to sequential inference if batch functions aren't available.
    """
    if not user_states:
        return {}
    
    # Try batch inference first (much faster for many users)
    if BATCH_INFERENCE_AVAILABLE:
        try:
            result = adapter.predict_users_batch(user_states, cloudlets)
            successful = len(result)
            total = len(user_states)
            if successful < total:
                logger.info(
                    f"Batch prediction: {successful}/{total} users predicted successfully"
                )
            return result
        except Exception as e:
            logger.warning(f"Batch inference failed, falling back to sequential: {e}")
    
    # Fallback to sequential inference
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
            f"Sequential prediction: {successful}/{total_users} users predicted, "
            f"{insufficient_history_count} users lack sufficient history"
        )
    if failed_count > 0:
        logger.warning(
            f"Sequential prediction: {failed_count} users failed due to errors"
        )
    
    return result
