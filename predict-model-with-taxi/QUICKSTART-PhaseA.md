# T-Drive Phase A — Quickstart

End-to-end guide to prepare data, train a simple GRU baseline, and evaluate on the T‑Drive dataset (without map‑matching).

## 1) Prerequisites

- Python 3.9–3.11 recommended (use your virtual env if available)
- Install packages inside your venv:

```powershell
pip install -U pip
pip install numpy pandas pyproj torch tqdm
# If PyTorch fails, try CPU-only wheels:
# pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## 2) Project layout and where to run

- Run commands from the folder: `predict-model-with-taxi`
- Dataset lives at: `T-drive Taxi Trajectories\release\taxi_log_2008_by_id`
- CLI module: `tdrive_predictor.cli`

## 3) Prepare data (Phase A)

Creates per-minute sequences with features and splits by day. Uses UTM Zone 50N (meters). No OSM/map‑matching yet.

Example (50 taxis, 15‑minute idle gap):

```powershell
cd predict-model-with-taxi
python -m tdrive_predictor.cli prepare `
  --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" `
  --num-taxis 50 `
  --max-idle-gap-min 15 `
  --out-dir tdrive_predictor_artifacts\phase_a
```

Outputs in `tdrive_predictor_artifacts\phase_a`:
- `train.pkl`, `val.pkl`, `test.pkl` — per-minute feature tables
- `scaler.pkl` — z‑score stats fitted on train
- `meta.json` — metadata (CRS, horizons, lookback, gap, etc.)

Tip: For a larger run use `--num-taxis 500`.

## 4) Train GRU baseline

Trains a GRU that predicts Δx,Δy for horizons {1,3,5,10} minutes.

```powershell
python -m tdrive_predictor.cli train `
  --data-dir tdrive_predictor_artifacts\phase_a `
  --epochs 10 `
  --lookback 20 `
  --batch-size 64
```

Output:
- `gru_phase_a.pt` saved under `tdrive_predictor_artifacts\phase_a`
- Training log prints train/val loss per epoch

## 5) Evaluate on test set

```powershell
python -m tdrive_predictor.cli eval `
  --data-dir tdrive_predictor_artifacts\phase_a
```

Prints metrics:
- `ADE` (m), `FDE` (m), `Hit@100/200/400` (fraction within radius, final step)

### CTRV baseline (optional)

Evaluate a classical EKF baseline without training:

```powershell
python -m tdrive_predictor.cli eval-ctrv `
  --data-dir tdrive_predictor_artifacts\phase_a `
  --lookback 20 `
  --r-pos 20.0 --q-pos 0.5 --q-v 0.5 --q-psi 0.01 --q-omega 0.005
```

This runs an EKF over each trip and rolls out 1/3/5/10-minute predictions, then reports the same metrics as the GRU.

## 6) Sanity checks

- Count rows and NaNs (should be zero in features):
```powershell
python - << 'PY'
import os, pandas as pd
p='predict-model-with-taxi/tdrive_predictor_artifacts/phase_a/train.pkl'
df=pd.read_pickle(p)
print('rows', len(df), 'total_nans', int(df.isna().sum().sum()))
print('days', sorted(df['ts'].dt.day.unique().tolist()))
PY
```

## 7) Troubleshooting

- ModuleNotFoundError: tdrive_predictor
  - Ensure you run commands inside `predict-model-with-taxi` so Python sees the package.
- FileNotFoundError: gru_phase_a.pt
  - Train step did not save a ckpt? Re-run train; the script now always saves final weights.
- NaN losses
  - Re-run prepare after the latest fixes; ensure `--max-idle-gap-min` is reasonable (e.g., 15–20) for sparse taxis.
- Nested artifacts path like `predict-model-with-taxi/predict-model-with-taxi/...`
  - Always use `--out-dir tdrive_predictor_artifacts\phase_a` and run from `predict-model-with-taxi`.

## 8) Notes

- Phase A is “free‑space” (no map‑matching). Phase B will add OSM loader, HMM, and road semantics.
- CRS: UTM Zone 50N (`EPSG:32650`) for metric computations; horizons: {1,3,5,10}; lookback L=20.
