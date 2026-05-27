# Change Notes - Session Dec 3, 2025

## Overview

This session focused on fixing bugs in the predictive scheduling system, improving experiment configuration, and fixing critical edge node placement issues for the serverless edge computing simulation.

---

## CRITICAL FIXES (Dec 3, 2025 - Latest)

### Central Node Relocation & Edge Placement

**Problem:** Central node was at (730, 1070) - near bottom-left of 1800x1200 map. Edge nodes were placed randomly around this off-center location, causing poor coverage and high turnaround times for ALL algorithms.

**Solution:** 
1. Moved central node to map center (900, 600)
2. Enabled grid-based placement for uniform coverage
3. Made edge node count configurable via `run_experiments.py`

**Files Modified:**
- `scheduler.py`: Central node location → (900, 600)
- `config.py`: Added `EXPECTED_TOTAL_EDGE_NODES` parameter
- `register_edge_node_controller.py`: Enabled grid placement, reads from Config
- `run_experiments.py`: Sets `EXPECTED_EDGE_NODES` environment variable

**Impact:** Expected 60-75% reduction in average user-to-edge distance.

---

## 1. Edge Node Distribution (Center-First Grid)

**File:** `serverless-sim/central_node/control_layer/controller_module/register_edge_node_controller.py`

**Problem:** Edge nodes were placed randomly around the central node, causing uneven coverage.

**Solution:** Implemented center-first grid distribution:
- Divide map into grid cells based on number of nodes
- Sort cells by distance from map center
- Assign nodes starting from center, spreading outward

**Example for 5 nodes (3x2 grid):**
```
+---+---+---+
| 3 | 2 | 4 |   <- Node 2 near center at row 0
+---+---+---+
| 5 | 1 | - |   <- Node 1 at map center!
+---+---+---+
```

**Parameters:**
- Map: 1800 x 1200 pixels (18km x 12km at 10m/pixel)
- Margin: 80 pixels
- Grid auto-calculated based on node count and aspect ratio

---

## 2. Dataset Configuration Fix

**Files:**
- `serverless-sim/run_experiments.py`
- `serverless-sim/central_node/control_layer/controller_module/set_dataset_controller.py`

**Problem:** Experiments were using `random_generated` data instead of `taxiD_Replay`, causing feature distribution mismatch with the trained predictive model.

**Solution:**
- Changed default dataset to `taxiD_Replay`
- Added sample size limit support for replay trajectories
- Updated experiment defaults: 100 users, 5 edge nodes

---

## 3. UI Sample Size Selector for TaxiD Replay

**File:** `simulation-ui/components/simulation/control-cards/DatasetSelectionCard.jsx`

**Problem:** UI only showed sample size selector for `random_generated`, not `taxiD_Replay`.

**Solution:** Added sample size selector for `taxiD_Replay` dataset with options: 100, 200, 300, ... 1000, 2000, 5000, 10000, 14000.

---

## Predictive Horizon Alignment (Dec 24, 2025)

**Problem:** Predictive scheduling was effectively using the last predictor horizon (t+10) for selecting the best edge node, which can be misaligned with the experiment loop cadence and the short warm-container TTL (default 8s), making “prewarm ahead” ineffective.

**Solution:** Switch the default horizon used for predictive selection to **t+5** (minutes), matching the TaxiD replay step (~1 minute per step) and the simulation’s execution cadence (every 5 steps).

**Files Modified:**
- `serverless-sim/config.py`: Added `PREDICTIVE_TARGET_HORIZON_MIN` (default `5`, env-overridable).
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`: Use `PREDICTIVE_TARGET_HORIZON_MIN` to choose the horizon column (defaults to `h5` for (1,3,5,10)).

**How to override:** set `PREDICTIVE_TARGET_HORIZON_MIN` to `1`, `3`, `5`, or `10` in the environment when starting central.

---

## Sticky Function Per User (Dec 24, 2025)

**Goal:** Make warm/cold behavior meaningful for mobility experiments by ensuring each user invokes a stable logical function name (instead of a random name each call).

**What changed:**
- When enabled, `/execute` uses `function_name = fn_user_{user_id}` (sanitized), so the first execute on a node tends to be `cold`, subsequent executes (within warm TTL) are `warm`. This aligns coldstart with node migration much better.
- Optional `FUNCTION_NAME_BUCKETS` lets you hash users into K shared “functions” (reduce container count).

**Files modified:**
- `serverless-sim/config.py`: added `STICKY_FUNCTION_PER_USER` (default off) and `FUNCTION_NAME_BUCKETS`.
- `serverless-sim/central_node/api_layer/central_controller.py`: stable function naming + prefer warm reuse for same function when sticky is enabled.
- `serverless-sim/edge_node/api_layer/edge_controller.py`: same as central.

**How to enable:**
- PowerShell: `$env:STICKY_FUNCTION_PER_USER="1"` (optional: `$env:FUNCTION_NAME_BUCKETS="128"`)
- Linux: `export STICKY_FUNCTION_PER_USER=1` (optional: `export FUNCTION_NAME_BUCKETS=128`)

---

## Simulated Execution Mode + Predictive Prewarm-Only (Dec 24, 2025)

**Problem:** In large experiments, a single “timestep” can take minutes wall-clock due to many `/execute` calls. Docker warm TTL (`DEFAULT_MAX_WARM_TIME=8s`) becomes meaningless, so “prewarm in advance” cannot be evaluated fairly.

**Solution (two parts):**
1) Add `EXECUTION_MODE=simulated` to skip real `/execute` HTTP+Docker calls and assign `computation_delay` analytically using measured warm/cold penalties.
2) Add `PREDICTIVE_PREWARM_ONLY=1` predictive mode:
   - does **not** reassign users immediately based on the predicted horizon,
   - instead plans a future node `(planned_node_id, planned_step_id)` and switches only when due.

**Files modified:**
- `serverless-sim/config.py`: added `EXECUTION_MODE` and simulated timing knobs; added prewarm-only knobs (`PREDICTIVE_PREWARM_ONLY`, lead steps, planning interval).
- `serverless-sim/central_node/control_layer/models/node.py`: added fields for simulated execution + planning (`last_executed_node_id`, `planned_node_id`, etc.).
- `serverless-sim/central_node/control_layer/controller_module/get_all_users_controller.py`: when `EXECUTION_MODE=simulated`, sets `container_status` and `computation_delay` without calling `/execute`; also syncs `current_step_id` before calling `node_assignment()` for TaxiD replay.
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`: implements prewarm-only planning/switching logic.

**Suggested env for experiments:**
- PowerShell:
  - `$env:EXECUTION_MODE="simulated"`
  - `$env:PREDICTIVE_PREWARM_ONLY="1"`
  - `$env:PREDICTIVE_TARGET_HORIZON_MIN="5"`
- Linux:
  - `export EXECUTION_MODE=simulated`
  - `export PREDICTIVE_PREWARM_ONLY=1`
  - `export PREDICTIVE_TARGET_HORIZON_MIN=5`

## 4. Trajectory Export Script Enhancement

**File:** `serverless-sim/scripts/export_taxid_replay_last1k.py`

**New Features:**
- `--include-features`: Export pre-computed features (v, a, delta_v, heading, etc.)
- `--selection {first,last,random}`: Choose which trajectories to export
- `--num-trips N`: Specify number of trajectories (or "all")
- Dynamic output filename based on parameters
- Progress bar with tqdm

**Usage:**
```bash
python serverless-sim/scripts/export_taxid_replay_last1k.py \
    --num-trips 100 \
    --include-features \
    --selection first
# Output: serverless-sim/mock_data/taxid_replay_100_features.pkl
```

---

## 5. Feature Handling in Simulation

**Files:**
- `serverless-sim/central_node/control_layer/controller_module/set_dataset_controller.py`
- `serverless-sim/central_node/control_layer/controller_module/get_all_users_controller.py`
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`

**Changes:**
- Load and detect feature availability in replay data
- Use pre-computed features directly when available
- Added `update_user_node_with_features()` method to scheduler
- Avoid re-calculating features when they exist in source data

---

## 6. Coordinate System Consistency

**File:** `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`

**Problem:** UI uses pixels, but prediction model was trained on meters.

**Solution:**
- Convert pixel coordinates to meters before storing in history
- Use `Config.DEFAULT_PIXEL_TO_METERS = 10` (1 pixel = 10 meters)
- Ensure all distance calculations are in meters

---

## 7. Configuration Updates

**File:** `serverless-sim/config.py`

**New/Updated Parameters:**
```python
DEFAULT_PIXEL_TO_METERS = 10  # 1 pixel = 10 m
TAXID_VIEWPORT_WIDTH_PX = 1800
TAXID_VIEWPORT_HEIGHT_PX = 1200
TAXID_VIEWPORT_MARGIN_PX = 80
TAXID_REPLAY_PATH = "mock_data/taxid_replay_last1k.pkl"
```

---

## Files Changed Summary

| File | Type | Description |
|------|------|-------------|
| `register_edge_node_controller.py` | Modified | Center-first grid distribution |
| `run_experiments.py` | Modified | Dataset & config changes |
| `set_dataset_controller.py` | Modified | Sample size support, feature loading |
| `get_all_users_controller.py` | Modified | Feature handling |
| `scheduler.py` | Modified | Coordinate conversion, feature methods |
| `DatasetSelectionCard.jsx` | Modified | UI sample size for taxiD_Replay |
| `export_taxid_replay_last1k.py` | Modified | New export options |
| `config.py` | Modified | New parameters |

---

## How to Run Experiment

**Terminal 1 (Central Node):**
```bash
cd ~/Serverless-edge-computing-simulation/serverless-sim
python central_main.py
```

**Terminal 2 (Experiment):**
```bash
cd ~/Serverless-edge-computing-simulation/serverless-sim
python run_experiments.py
```

**Current Default Config:**
- Users: 100
- Edge Nodes: 5 (center-first grid)
- Algorithms: ["predictive", "greedy"]
- Dataset: taxiD_Replay
- Duration: 50 timesteps

---

## Known Issues / TODO

1. Batch inference for predictive mode needs further optimization
2. Connection pool warnings when running with many users
3. Cold start penalty calculation may need tuning

---

## Predictor UX Improvements (Dec 17, 2025)

**Problem:** Running `python -m tdrive_predictor.cli eval --mode curv_step` on large Phase B artifacts (e.g. 7k) could appear “stuck” for hours with no console output.

**Solution:**
- Added explicit progress/log prints for eval startup and heavy load steps (meta/test/ckpt loading).
- Added a per-trip progress bar for `curv_step` evaluation (uses `tqdm` when available; otherwise prints periodic status).

**Files Modified:**
- `predict-model-with-taxi/tdrive_predictor/cli.py`
- `predict-model-with-taxi/tdrive_predictor/evaluate.py`

---

## Faster `curv_step` evaluation controls (Dec 17, 2025)

**Problem:** `python -m tdrive_predictor.cli eval --mode curv_step` on large Phase B artifacts (e.g., 7k) evaluates *all sliding windows* per trip (often ~60–80 windows/trip), leading to multi-hour runtimes even without `--graphml`.

**Solution:**
- Added optional eval flags to reduce evaluated windows (applies to `curv_step` only):
  - `--max-windows-per-trip N` (e.g., 1 or 5)
  - `--window-stride K` (evaluate every K-th window)
- Added `--device {auto,cpu,cuda}` for eval to explicitly choose GPU for the model forward pass.

**Files Modified:**
- `predict-model-with-taxi/tdrive_predictor/cli.py`
- `predict-model-with-taxi/tdrive_predictor/evaluate.py`

---

## Experiment results visualization (Dec 23, 2025)

**Goal:** Visualize `serverless-sim/experiment_results_*.csv` with clear scaling and summary stats, even on machines where `pandas/matplotlib` are broken due to NumPy ABI mismatches.

**Added:**
- `serverless-sim/scripts/plot_experiment_results.py`
  - Reads CSV with stdlib `csv` (no pandas).
  - Writes `summary.md` with mean/median/p95/p99 for:
    - total turnaround time (sum over users)
    - avg per user (ms/user)
  - Tries matplotlib first; if unavailable/broken, falls back to generating static `.svg` plots.
  - `--force-svg` flag to skip matplotlib entirely.

**Typical usage:**
```bash
cd serverless-sim
python scripts/plot_experiment_results.py --csv experiment_results_20251223_195950.csv --out-dir plots/experiment_results_20251223_195950
```

python scripts/plot_experiment_results.py --csv experiment_results_20251228_131147.csv --out-dir plots/experiment_results_20251228_131147.csv

---

## Allow sample_size > 1000 for TaxiD replay (Dec 24, 2025)

**Problem:** `run_experiments.py` failed to set dataset when `sample_size` (num_users) was > 1000 (HTTP 400: "Sample size must be a positive integer not exceeding 1000.").

**Change:**
- Removed the hard upper bound (1000) in dataset validation; now `sample_size` only needs to be a positive integer.

**File Modified:**
- `serverless-sim/central_node/control_layer/controller_module/set_dataset_controller.py`

---

## Add warm/cold turnaround breakdown in experiments (Dec 29, 2025)

**Problem:** When running `EXECUTION_MODE=simulated`, total turnaround time spikes (e.g. around timestep ~20) were hard to interpret because we only logged one aggregate number.

**Change:**
- Performance metrics endpoint now returns a breakdown of total turnaround time by `container_status`:
  - `total_turnaround_time_warm`, `total_turnaround_time_cold`, `total_turnaround_time_unknown`
  - `warm_count`, `cold_count`, `unknown_count`
- `run_experiments.py` records these fields per timestep into the experiment CSV and prints a compact warm/cold summary.

**Files Modified:**
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`
- `serverless-sim/central_node/control_layer/controller_module/get_performance_metrics_controller.py`
- `serverless-sim/run_experiments.py`

---

## Fix predictive prewarm-only to actually count as warm on switch step (Dec 29, 2025)

**Problem:** In `PREDICTIVE_PREWARM_ONLY` mode, the scheduler cleared `(planned_node_id, planned_step_id)` immediately when applying a due switch. Since execution is simulated *after* `node_assignment()`, the warm-check never saw the plan on the switch step, so switches were still counted as cold.

**Change (B1):**
- Keep `(planned_node_id, planned_step_id)` during the switch step (`current_step == planned_step_id`) so the execution layer can mark it warm.
- Clear the plan on later steps (`current_step > planned_step_id`) to avoid re-applying.

**File Modified:**
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`

---

## Plot cold-start metrics in experiment plots (Dec 29, 2025)

**Goal:** For new experiment CSV format (with warm/cold breakdown), plot and summarize cold-start behavior.

**Added to plots:**
- Cold start count vs timestep (`coldstart_count.png` / `.svg`)
- Cold-start turnaround time (sum over cold users) vs timestep (`coldstart_time_ms.png` / `.svg`)

**Added to `summary.md`:**
- Percent difference of mean total turnaround time (predictive vs greedy).

**File Modified:**
- `serverless-sim/scripts/plot_experiment_results.py`

---

## Enable env-config for predictive prewarm-only mode (Dec 29, 2025)

**Problem:** Scheduler and execution layer check `Config.PREDICTIVE_PREWARM_ONLY`, but `Config` did not read these env vars, so setting `PREDICTIVE_PREWARM_ONLY=1` had no effect (always False).

**Change:**
- Added env-backed config keys:
  - `PREDICTIVE_PREWARM_ONLY`
  - `PREDICTIVE_PREWARM_LEAD_STEPS`
  - `PREDICTIVE_EXECUTE_INTERVAL_STEPS`

**File Modified:**
- `serverless-sim/config.py`

---

## Improve edge node spatial distribution on registration (Dec 30, 2025)

**Problem:** Edge nodes were often placed clustered in one region (not visually “even” on the UI). This happened especially when `EXPECTED_EDGE_NODES` was not perfectly aligned with the actual number of started edges, and because the previous placement sorted grid cells “center-first”.

**Change:**
- Updated the grid placement strategy to use **farthest-point sampling** over grid cell centers:
  - First node is anchored near the **current central node location** (if available), otherwise the map center.
  - Subsequent nodes pick the cell that maximizes the minimum distance to already chosen cells.
- This produces a more even spread for the first few nodes and avoids clumping.

**File Modified:**
- `serverless-sim/central_node/control_layer/controller_module/register_edge_node_controller.py`

**Additional integration:**
- When selecting `taxiD` / `taxiD_Replay` dataset, the dataset setup recenters the central node based on road-graph bounds. Edge nodes may have been registered *before* dataset selection, so they could appear clustered/offset in the UI.
- Added a step to re-spread existing edge nodes right after recentering the central node during dataset setup.

**File Modified:**
- `serverless-sim/central_node/control_layer/controller_module/set_dataset_controller.py`

---

## Fix TaxiD replay default pickle path (Dec 30, 2025)

**Problem:** `taxiD_Replay` dataset loading was hardcoded to look for `serverless-sim/mock_data/taxid_replay_5000_features.pkl`, causing `FileNotFoundError` when only `taxid_replay_last1k.pkl` existed.

**Change:**
- Updated replay loader candidate list to try (in order):
  - `serverless-sim/mock_data/taxid_replay_last1k.pkl`
  - `serverless-sim/mock_data/taxid_replay_last1k_features.pkl`
  - `serverless-sim/mock_data/taxid_replay_5000_features.pkl`
- Still supports overriding via `TAXID_REPLAY_PATH` env var.

**File Modified:**
- `serverless-sim/central_node/control_layer/controller_module/set_dataset_controller.py`

---

## Fix prewarm-only plan overwrite on switch step (Jan 16, 2026)

**Problem:** With `EXECUTION_MODE=simulated` and `PREDICTIVE_PREWARM_ONLY=1`, prewarm-only is supposed to count the *switch step* as warm when `planned_step_id == current_step`. However, on planning ticks (e.g. every 5 steps), the scheduler would apply the due switch and then immediately re-run planning in the same timestep, overwriting `planned_step_id` from `current_step` to `current_step + lead_steps`. This caused the execution layer to miss the `planned_step_id == step_id` condition, producing a large cold-start burst at the switch timestep (e.g. step 25).

**Change:**
- During the planning loop in `_predictive_prewarm_only_assignment()`, skip updating `planned_node_id/planned_step_id` for users whose `planned_step_id == current_step` (i.e., switching now). This keeps the plan fields intact for the current timestep so the simulated execution can mark the switch as warm. The next plan will be computed on a later planning tick.

**File Modified:**
- `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`

---

# Change Notes — Session 2026-04-16

## Horizon-Aligned Attention Decoder cho trajectory predictor

### Context & motivation

- `GRUStepDecoderRoad` ([model.py:47-87](predict-model-with-taxi/tdrive_predictor/model.py#L47-L87)) predict 10 step Δs (mỗi step 1 phút), nhưng serverless-sim scheduler **chỉ consume h=5** ở cả 2 chỗ planning ([scheduler.py:527](serverless-sim/central_node/control_layer/scheduler_module/scheduler.py#L527), [scheduler.py:671](serverless-sim/central_node/control_layer/scheduler_module/scheduler.py#L671)), khớp với `PREDICTIVE_PREWARM_LEAD_STEPS=5` ([config.py:134](serverless-sim/config.py#L134)).
- Kết quả 7k_fast: h1 ADE=27.7m, **h5 ADE=240.8m**, h10=417.7m. h5 error gấp ~9× h1, một phần do **information bottleneck** (decoder chỉ nhận `h_T` — 1 vector nén 20 timesteps — rồi autoregressive qua 5 bước).
- Loss weighting hiện tại: default `ones(10)`; `TDRIVE_CURVSTEP_WEIGHTED_LOSS=1` → `[1,1,1,1,0.8,0.8,0.8,0.8,0.7,0.7]` (đang down-weight đúng h=5 — ngược hướng mong muốn).

Hai thay đổi complementary, kết hợp thành 1 experiment:
1. **Bahdanau attention decoder** — mở information channel cho mọi horizon; decoder query encoder outputs tại mỗi step.
2. **Peaked h=5 horizon weighting** — allocate gradient budget cho horizon scheduler consume.

### Files modified

| File | Action |
|---|---|
| `predict-model-with-taxi/tdrive_predictor/model.py` | Thêm class `GRUStepDecoderRoadAttn` (~50 LOC), giữ class cũ nguyên |
| `predict-model-with-taxi/tdrive_predictor/train.py` | Thêm 2 env flag, model-selection logic, peaked-h5 weight branch, ckpt tên riêng, ghi `arch` vào `meta.json` |
| `predict-model-with-taxi/tdrive_predictor/inference_service.py` | `_build_model(..., arch=...)` route class; `load_predictor_bundle` đọc `meta["arch"]`, fallback sniff state_dict có `W_attn`/`V_attn` không |

Không đổi: dataset, evaluate.py, scheduler serverless-sim, config.py, output shape model.

### Chi tiết thay đổi

**1. `GRUStepDecoderRoadAttn`** (`model.py`)
- Encoder giữ nguyên (GRU). Decoder mỗi step:
  - Bahdanau additive attention: `scores = V_attn(tanh(W_attn(h) + U_attn(enc_out)))`, softmax → context [B, H].
  - `GRUCell(input_size=1 + H)` nhận `[prev_pred, context]` concat.
  - `U_attn(enc_out)` precompute 1 lần/forward để tránh compute lại trong loop.
  - Scheduled sampling / teacher forcing logic copy nguyên từ class cũ.
- Param cost (H=512): +~1.05M (+56%, total ~2.9M, vẫn ~12MB FP32).

**2. Env flags & selection** (`train.py`)
- `TDRIVE_CURVSTEP_ATTN=1` → train class Attn, ckpt `gru_phase_curv_step_attn.pt`, `meta.arch = "gru_step_attn"`.
- `TDRIVE_CURVSTEP_PEAKED_H5=1` → weights `[0.3, 0.5, 0.8, 1.2, 1.6, 1.2, 0.8, 0.5, 0.3, 0.2]` (peak @ h5).
- Priority: `PEAKED_H5` > `WEIGHTED_LOSS` > uniform.
- Giữ `TDRIVE_CURVSTEP_HIGH_SS=1` tương thích ngược.

**3. Inference routing** (`inference_service.py`)
- Đọc `meta["arch"]` → chọn `GRUStepDecoderRoad` hoặc `GRUStepDecoderRoadAttn`.
- Fallback khi `arch` thiếu: sniff keys `W_attn.*` / `V_attn.*` trong state_dict.
- Default checkpoint filename route theo arch cho `curv_step`.

### Hướng dẫn chạy

**Prerequisites**
- Phase B dataset build xong (có `train.pkl`, `val.pkl`, `test.pkl`, `meta.json`, `scaler.pkl`).
- GPU khuyến nghị cho 7k_fast (80 epochs, H=512, batch=256). CPU OK smoke test.
- Mỗi config dùng artifact dir riêng để không đè baseline:

```bash
cd predict-model-with-taxi/tdrive_predictor_artifacts
cp -r phase_b_7k_fast phase_b_7k_fast_attn_peaked
rm phase_b_7k_fast_attn_peaked/gru_phase_curv_step*.pt
```

**Training — 6 configs ablation**

Chạy từ `predict-model-with-taxi/`. Common args: `--mode curv_step --batch-size 256 --epochs 80 --early-stop-patience 6 --target-scale 100`.

```bash
# A — baseline (GRU-512, uniform)
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 512 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast

# B — peaked-h5 only
TDRIVE_CURVSTEP_PEAKED_H5=1 \
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 512 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_peaked

# C — attention only
TDRIVE_CURVSTEP_ATTN=1 \
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 512 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_attn

# D — PROPOSED: attention + peaked-h5
TDRIVE_CURVSTEP_ATTN=1 TDRIVE_CURVSTEP_PEAKED_H5=1 \
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 512 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_attn_peaked

# E — lightweight combined (GRU-128)
TDRIVE_CURVSTEP_ATTN=1 TDRIVE_CURVSTEP_PEAKED_H5=1 \
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 128 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_lite_attn_peaked

# F — lightweight baseline (GRU-128, uniform)
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 128 --batch-size 256 \
  --epochs 80 --early-stop-patience 6 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_lite
```

Windows PowerShell: thay `VAR=... command` bằng `$env:VAR="1"; command` (mỗi flag 1 dòng).

**Smoke test nhanh (khuyến nghị trước full train)**

Dùng dataset nhỏ, 5-10 epochs, chỉ verify không NaN và loss giảm:

```bash
TDRIVE_CURVSTEP_ATTN=1 TDRIVE_CURVSTEP_PEAKED_H5=1 \
python -m tdrive_predictor.cli train \
  --mode curv_step --hidden-size 256 --batch-size 128 \
  --epochs 10 --target-scale 100 \
  --data-dir tdrive_predictor_artifacts/phase_b_1k_fast_smoke
```

**Offline evaluation**

```bash
python -m tdrive_predictor.cli evaluate \
  --mode curv_step \
  --data-dir tdrive_predictor_artifacts/phase_b_7k_fast_attn_peaked
```

Chạy cho mỗi artifact dir, export bảng ADE/FDE/Hit@200 tại h=1, 3, 5, 10 cho cả 6 configs.

**Simulation eval (downstream)**

```bash
# Linux/macOS
export EXECUTION_MODE=simulated
export TDRIVE_ARTIFACT_DIR=$(pwd)/predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_7k_fast_attn_peaked
export PREDICTIVE_PREWARM_ONLY=1
export STICKY_FUNCTION_PER_USER=1
cd serverless-sim && python web_start.py
```

```powershell
# Windows PowerShell
$env:EXECUTION_MODE="simulated"
$env:TDRIVE_ARTIFACT_DIR="$PWD\predict-model-with-taxi\tdrive_predictor_artifacts\phase_b_7k_fast_attn_peaked"
$env:PREDICTIVE_PREWARM_ONLY="1"
$env:STICKY_FUNCTION_PER_USER="1"
cd serverless-sim; python web_start.py
```

Chạy cùng scenario (TaxiD_Replay, seed cố định, cùng số user + thời gian) cho từng config, collect metrics từ `/api/v1/central/metrics`: avg turnaround_time, cold_start_rate, migration_count.

### Expected impact (D vs A)

| Metric | Baseline (A) | Proposed (D) | Δ |
|---|---|---|---|
| ADE h1 | 27.7m | 30-33m | +10-20% (unused bởi scheduler) |
| **ADE h5** | **240.8m** | **195-210m** | **-13 to -19%** |
| ADE h10 | 417.7m | 440-470m | +5-12% (unused) |
| Turnaround time (sim) | baseline | giảm 5-8% | — |
| Cold start rate (sim) | baseline | giảm 8-12% | — |

### Backward compatibility

- Baseline checkpoints (`gru_phase_curv_step.pt` không có `arch` trong meta) vẫn load bình thường qua fallback sniffing.
- Mọi flag mới default OFF → run mặc định y hệt trước session này.
- Shape output [B, 10] không đổi → scheduler serverless-sim không cần update.
