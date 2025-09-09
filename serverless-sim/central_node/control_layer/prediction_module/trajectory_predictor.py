"""
Trajectory Predictor wrapper
Tries to use Spatial-Temporal GNN if available; otherwise falls back to simple
linear extrapolation from recent coordinates.
"""

from typing import List, Tuple, Optional
import os


class TrajectoryPredictor:
    def __init__(self, model_path: Optional[str] = None, sequence_length: int = 5):
        self.model = None
        self.sequence_length = sequence_length
        self.using_gnn = False

        # Lazy import tensorflow to avoid heavy dependency if not needed
        if model_path and os.path.exists(model_path):
            try:
                import tensorflow as tf  # noqa: F401
                from tensorflow import keras
                self.model = keras.models.load_model(model_path, compile=False)
                self.using_gnn = True
            except Exception:
                # Fallback gracefully
                self.model = None
                self.using_gnn = False

    def predict_next(self, coords_seq: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        Predict next (x,y) from recent sequence of coordinates.
        coords_seq: list of (x,y) with oldest first.
        """
        if not coords_seq:
            return 0.0, 0.0

        # If GNN is available and we have enough history, attempt to use it
        if self.model and len(coords_seq) >= self.sequence_length:
            try:
                import numpy as np
                seq = coords_seq[-self.sequence_length:]
                # Simple feature: concatenate x,y per timestep; pad to fixed size
                # Model expects (batch, timesteps, features). We'll pass 2 features (x,y).
                X = np.array(seq, dtype=float).reshape(1, self.sequence_length, 2)
                pred = self.model.predict(X, verbose=0)
                if isinstance(pred, list):
                    pred = pred[0]
                px, py = float(pred[0]), float(pred[1])
                return px, py
            except Exception:
                pass  # fallback below

        # Fallback: linear extrapolation using last 2 points
        if len(coords_seq) >= 2:
            x1, y1 = coords_seq[-2]
            x2, y2 = coords_seq[-1]
            dx, dy = x2 - x1, y2 - y1
            return x2 + dx, y2 + dy

        # Only one point available
        return coords_seq[-1]

