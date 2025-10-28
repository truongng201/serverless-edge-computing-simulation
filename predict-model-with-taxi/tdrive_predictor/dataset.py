"""
Sequence dataset builder for Phase A GRU model.

This module converts a per-minute, per-trip flattened DataFrame (produced by
prepare.py) into sliding-window sequences of length L with multi-horizon
displacement targets (Δx, Δy) for horizons [1, 3, 5, 10] minutes.

Input expectations
------------------
- DataFrame columns must include:
  - 'trip_id' : groups rows that belong to the same trip
  - 'ts'      : per-minute DateTimeIndex-like column (monotonic per trip)
  - 'x','y'   : UTM coordinates in meters (positions at each minute)
  - feature columns: normalized features listed by `feature_cols`
- Rows are assumed sorted by (trip_id, ts); the class will enforce sorting.

Outputs
-------
- Each dataset item returns a tuple (x_seq, y_target, base_pos):
  - x_seq    : torch.float32 tensor [L, F] with the lookback window features
  - y_target : torch.float32 tensor [8] with Δx,Δy for horizons 1,3,5,10
               in the order [dx1,dy1, dx3,dy3, dx5,dy5, dx10,dy10]
  - base_pos : torch.float32 tensor [2] with (x0,y0) at current time t (end of window),
               useful for reconstructing absolute positions during evaluation
"""

from typing import List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class SequenceHorizonDataset(Dataset):
    """Slice a flattened per-minute table into sequences and multi-horizon targets.

    The dataset iterates over sliding windows of length `lookback` entirely inside
    a single trip (no cross-trip windows). For each window ending at time t, it
    produces targets for the next horizons h ∈ {1,3,5,10} minutes as displacements
    relative to the position at t.
    """

    def __init__(self, df: pd.DataFrame, feature_cols: List[str], lookback: int = 20):
        super().__init__()
        # Ensure deterministic ordering by trip and timestamp
        self.df = df.sort_values(['trip_id', 'ts']).reset_index(drop=True)
        self.feature_cols = feature_cols
        self.lookback = int(lookback)
        # Precompute (start,end) row indices for all valid windows.
        # Each tuple defines an inclusive window [start, end] of length L.
        self.examples: List[Tuple[int, int]] = []
        # Build windows trip-by-trip to prevent crossing boundaries
        for trip_id, g in self.df.groupby('trip_id'):
            n = len(g)
            # Need enough future to cover the farthest horizon (+10 minutes)
            if n < self.lookback + 10:
                continue
            base = g.index.min()  # starting index of this trip within df
            # end index goes from (base+L-1) up to the last index that still allows +10
            for end in range(base + self.lookback - 1, base + n):
                steps = [1, 3, 5, 10]
                max_needed = end + steps[-1]
                if max_needed >= base + n:
                    break  # not enough future rows for the 10-minute target
                start = end - (self.lookback - 1)
                self.examples.append((start, end))

    def __len__(self) -> int:
        # Total number of available windows across all trips
        return len(self.examples)

    def __getitem__(self, idx: int):
        # Retrieve window bounds
        start, end = self.examples[idx]
        # Slice window rows [start, end]
        rows = self.df.iloc[start : end + 1]
        # Assemble feature tensor [L, F]
        x_seq = torch.tensor(rows[self.feature_cols].to_numpy(dtype=np.float32))
        # Position at current time t (end of window), used as reference for targets
        x0 = float(rows['x'].iloc[-1])
        y0 = float(rows['y'].iloc[-1])
        # Build multi-horizon displacement targets relative to (x0,y0)
        # We assume per-minute rows, so +s corresponds to s rows ahead
        base_end = end
        steps = [1, 3, 5, 10]
        targs = []  # [dx1, dy1, dx3, dy3, dx5, dy5, dx10, dy10]
        for s in steps:
            row = self.df.iloc[base_end + s]
            dx = float(row['x'] - x0)
            dy = float(row['y'] - y0)
            targs.append(dx)
            targs.append(dy)
        y_target = torch.tensor(np.array(targs, dtype=np.float32))  # [8]
        # Also return base position (x0,y0) to reconstruct absolute coords later
        base_pos = torch.tensor([x0, y0], dtype=torch.float32)
        return x_seq, y_target, base_pos
