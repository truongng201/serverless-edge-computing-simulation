# Change Notes - Session Dec 3, 2025

## Overview

This session focused on fixing bugs in the predictive scheduling system and improving experiment configuration for the serverless edge computing simulation.

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

