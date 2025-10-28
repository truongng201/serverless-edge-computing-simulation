"""
CTRV (Constant Turn Rate and Velocity) EKF baseline.

This baseline filters per-minute positions (x,y in meters, UTM) and then rolls
out predictions 1,3,5,10 minutes ahead using predict-only steps. It does not
require training and serves as a classical non-DL reference.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class CTRVParams:
    dt: float = 60.0  # seconds
    eps_omega: float = 1e-3
    # process noise stds (tunable)
    q_pos: float = 0.5  # m
    q_v: float = 0.5    # m/s
    q_psi: float = 0.01 # rad
    q_omega: float = 0.005  # rad/s
    # measurement noise std (position)
    r_pos: float = 20.0  # m


def _ctrv_f(x: np.ndarray, dt: float, eps_omega: float) -> np.ndarray:
    """Nonlinear CTRV state transition.
    x = [x, y, v, psi, omega].
    """
    px, py, v, psi, omega = x
    if abs(omega) > eps_omega:
        px2 = px + v / omega * (np.sin(psi + omega * dt) - np.sin(psi))
        py2 = py + v / omega * (-np.cos(psi + omega * dt) + np.cos(psi))
        psi2 = psi + omega * dt
    else:
        px2 = px + v * dt * np.cos(psi)
        py2 = py + v * dt * np.sin(psi)
        psi2 = psi
    v2 = v
    omega2 = omega
    return np.array([px2, py2, v2, psi2, omega2], dtype=float)


def _jacobian_F(x: np.ndarray, dt: float, eps_omega: float) -> np.ndarray:
    """Numerical Jacobian of f(x) via central differences (robust, simple)."""
    n = x.shape[0]
    F = np.zeros((n, n), dtype=float)
    fx = _ctrv_f(x, dt, eps_omega)
    eps = 1e-5
    for i in range(n):
        dx = np.zeros(n)
        dx[i] = eps
        f1 = _ctrv_f(x + dx, dt, eps_omega)
        f2 = _ctrv_f(x - dx, dt, eps_omega)
        F[:, i] = (f1 - f2) / (2 * eps)
    return F


def _ekf_step(x: np.ndarray, P: np.ndarray, z: np.ndarray, params: CTRVParams) -> Tuple[np.ndarray, np.ndarray]:
    # Predict
    F = _jacobian_F(x, params.dt, params.eps_omega)
    x_pred = _ctrv_f(x, params.dt, params.eps_omega)
    Q = np.diag([
        params.q_pos**2,
        params.q_pos**2,
        params.q_v**2,
        params.q_psi**2,
        params.q_omega**2,
    ])
    P_pred = F @ P @ F.T + Q
    # Update (measurement z = [x, y])
    H = np.array([[1, 0, 0, 0, 0],
                  [0, 1, 0, 0, 0]], dtype=float)
    R = np.diag([params.r_pos**2, params.r_pos**2])
    y = z - (H @ x_pred)
    S = H @ P_pred @ H.T + R
    K = P_pred @ H.T @ np.linalg.inv(S)
    x_new = x_pred + K @ y
    I = np.eye(5)
    P_new = (I - K @ H) @ P_pred
    return x_new, P_new


def _init_state_from_points(p0: Tuple[float, float], p1: Tuple[float, float], dt: float) -> np.ndarray:
    x0, y0 = p0
    x1, y1 = p1
    vx = (x1 - x0) / dt
    vy = (y1 - y0) / dt
    v = float(np.hypot(vx, vy))
    psi = float(np.arctan2(vy, vx))
    omega = 0.0
    return np.array([x0, y0, v, psi, omega], dtype=float)


def filter_trip(trip: pd.DataFrame, params: CTRVParams) -> List[np.ndarray]:
    """Run EKF forward pass over a single trip, return filtered states per row.
    Expects columns: ['ts','x','y'] and uniform cadence (60s).
    """
    dt = params.dt
    xs = []
    n = len(trip)
    if n == 0:
        return xs
    # init using first two points (or duplicate first if needed)
    if n >= 2:
        x = _init_state_from_points((trip['x'].iloc[0], trip['y'].iloc[0]),
                                    (trip['x'].iloc[1], trip['y'].iloc[1]), dt)
    else:
        # degenerate
        x = np.array([trip['x'].iloc[0], trip['y'].iloc[0], 0.0, 0.0, 0.0], dtype=float)
    P = np.diag([25.0, 25.0, 4.0, 0.1, 0.01])  # initial covariance
    # first measurement update to anchor to the first observation
    z0 = np.array([trip['x'].iloc[0], trip['y'].iloc[0]], dtype=float)
    x, P = _ekf_step(x, P, z0, params)
    xs.append(x.copy())
    # iterate remaining measurements
    for i in range(1, n):
        z = np.array([trip['x'].iloc[i], trip['y'].iloc[i]], dtype=float)
        x, P = _ekf_step(x, P, z, params)
        xs.append(x.copy())
    return xs


def rollout_horizons(x_t: np.ndarray, steps: List[int], params: CTRVParams) -> List[Tuple[float, float]]:
    """Predict positions at t+steps (in minutes) using CTRV predict-only steps."""
    preds = []
    # copy state
    x = x_t.copy()
    base_pos = (x[0], x[1])
    # simulate up to max step, caching intermediate positions
    max_step = max(steps)
    cache = {}
    for s in range(1, max_step + 1):
        x = _ctrv_f(x, params.dt, params.eps_omega)
        cache[s] = (x[0], x[1])
    for s in steps:
        px, py = cache[s]
        dx = px - base_pos[0]
        dy = py - base_pos[1]
        preds.append((dx, dy))
    return preds


def eval_ctrv_on_split(df: pd.DataFrame, lookback: int = 20, params: CTRVParams = CTRVParams()) -> Tuple[np.ndarray, np.ndarray]:
    """Compute CTRV predictions and targets aligned to GRU windows.

    For each trip, we filter states per-minute, then for each window end index t
    with enough history (>=lookback) and future (>=10 minutes), we produce:
      - y_pred: [dx1,dy1, dx3,dy3, dx5,dy5, dx10,dy10]
      - y_true: same computed from ground truth positions
    Returns stacks over all windows across trips.
    """
    preds = []
    truths = []
    steps = [1, 3, 5, 10]
    for trip_id, g in df.sort_values(['trip_id', 'ts']).groupby('trip_id'):
        g = g.reset_index(drop=True)
        n = len(g)
        if n < lookback + max(steps):
            continue
        # filter states for this trip
        states = filter_trip(g[['ts', 'x', 'y']], params)
        # iterate valid window ends
        for end in range(lookback - 1, n - max(steps)):
            x_t = states[end]
            # predicted displacements
            pred_pairs = rollout_horizons(x_t, steps, params)
            y_pred = []
            for (dx, dy) in pred_pairs:
                y_pred.extend([dx, dy])
            preds.append(y_pred)
            # true displacements
            x0 = g['x'].iloc[end]
            y0 = g['y'].iloc[end]
            y_true = []
            for s in steps:
                row = g.iloc[end + s]
                y_true.extend([float(row['x'] - x0), float(row['y'] - y0)])
            truths.append(y_true)
    if len(preds) == 0:
        return np.zeros((0, 8), dtype=np.float32), np.zeros((0, 8), dtype=np.float32)
    return np.array(preds, dtype=np.float32), np.array(truths, dtype=np.float32)

