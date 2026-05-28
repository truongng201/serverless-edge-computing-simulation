# tdrive_predictor Developer Notes

This doc explains how the current code prepares data, trains, evaluates models, supported model modes, and what each file in `tdrive_predictor/` does.

## Quick commands (from `predict-model-with-taxi`)

```bash
# Phase A (free-space)
python -m tdrive_predictor.cli prepare --tdrive-root "./T-drive Taxi Trajectories/release/taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts/phase_a
python -m tdrive_predictor.cli train   --data-dir tdrive_predictor_artifacts/phase_a --mode xy --lookback 20
python -m tdrive_predictor.cli eval    --data-dir tdrive_predictor_artifacts/phase_a --mode xy

# Phase B (OSM/HMM)
python -m tdrive_predictor.cli prepare --tdrive-root "./T-drive Taxi Trajectories/release/taxi_log_2008_by_id" --num-taxis 5000 --max-idle-gap-min 15 --use-osm --graphml ./osm/beijing_taxid.graphml --cand-radius-m 150 --k-candidates 8 --beam-size 20 --road-resample --out-dir tdrive_predictor_artifacts/phase_b_5k_fast
python -m tdrive_predictor.cli train   --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --lookback 20 --epochs 80 --batch-size 256 --hidden-size 512 --target-scale 1.0 --early-stop-patience 6 --early-stop-min-delta 0.1 --device cuda --num-workers 16
python -m tdrive_predictor.cli eval    --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --graphml ./osm/beijing_taxid.graphml
```

## Pipeline: prepare → train → eval

### Prepare (Phase A vs Phase B)
- **Input**: raw CSV logs `taxi_id, timestamp, lon, lat` from `T-drive Taxi Trajectories/release/taxi_log_2008_by_id/`.
- **Phase A** (free-space):
  - WGS84 → UTM 50N.
  - Segment trips with `--max-idle-gap-min`.
  - Resample per minute on union timeline; interpolate position.
  - Features: v, a, Δv, Δheading, stop_flag, dwell_time, tod_sin/cos, dow_sin/cos, rush_hour.
  - Split day-based (train/val/test).
- **Phase B** (OSM/HMM):
  - Map-match each GPS point to road graph using HMM (candidates via STRtree, emission Gaussian on distance, transition by path length vs Δt/vmax; optional shortest-path).
  - Build footpoints, resample per minute (time-based); optional `--road-resample` along road polylines.
  - Same feature set as Phase A, but coordinates are road-projected (m).
  - Split by trips (train/val/test).
- **Outputs** (in `out-dir`):
  - `train.pkl`, `val.pkl`, `test.pkl`: feature windows + targets.
  - `meta.json`: feature_cols, lookback, mode, HMM params, graph source.
  - `scaler.pkl`: z-score params.
  - Checkpoints after training.

Key HMM params:
- `--cand-radius-m`, `--k-candidates`, `--beam-size`, `--sigma-gps-m`, `--turn-penalty`, `--use-shortest-path`, `--road-resample`.

### Train
- Run `tdrive_predictor.train.train_gru`.
- Modes:
  - `xy` (free-space): predict Δx, Δy for horizons [1,3,5,10].
  - `curv`: predict Δs (curvilinear distance) for horizons [1,3,5,10].
  - `curv_step`: encoder-decoder predicts Δs step-by-step for 10 minutes (1’ steps).
- Important args: `--lookback`, `--batch-size`, `--hidden-size`, `--target-scale` (scales targets to help SmoothL1), `--early-stop-patience`, `--early-stop-min-delta`, `--device`, `--num-workers`.
- Loss: SmoothL1 with per-horizon weights; scheduled sampling for `curv_step`.
- Checkpoint saved as `gru_phase_curv_step.pt` (or `_curv`, `_a`).

### Eval
- `tdrive_predictor.evaluate.evaluate_gru` or `_evaluate_curv_step`.
- Metrics: ADE, FDE, Hit@100/200/400, Per-horizon error & Hit@200.
- With `--graphml` in eval (curv/curv_step), can map Δs along graph; otherwise Δs is projected along last heading (no snap-to-road).

## Model modes (current code)
- `GRUDisplacement` (xy): Δx, Δy free-space.
- `GRUDisplacementRoad` (curv): Δs for horizons; no per-step decoder.
- `GRUStepDecoderRoad` (curv_step): Δs per minute (10 steps); inference projects along last heading (no snap after each step in inference_service).

## File-by-file map (`tdrive_predictor/`)
- `cli.py`: CLI entry; subcommands `prepare`, `train`, `eval`, `eval-ctrv`, `eval-markov`.
- `prepare.py`: Full Phase A/B pipeline; segmentation, resample, feature build, HMM map-match (Phase B), write train/val/test pickles, scaler, meta.
- `train.py`: `train_gru` for xy/curv/curv_step; checkpointing, LR scheduler, early stop.
- `evaluate.py`: Eval for xy/curv/curv_step, optional graph-based traversal for Δs; prints ADE/FDE/Hit@R and per-horizon stats.
- `dataset.py`: PyTorch Dataset for sequence windows (lookback) and targets (Δx,Δy or Δs).
- `model.py`: GRU model definitions (see modes above).
- `metrics.py`: ADE/FDE, Hit@R, per-horizon utilities.
- `utils.py`: Helpers (speed filters, coord transforms, reading logs, chunk writers).
- `baselines/ctrv.py`: CTRV (EKF) baseline; optional snap-to-road in Phase B.
- `baselines/markov.py`: Hour-conditioned Markov on road segments.
- `osm/loader.py`: Load GraphML or build from OSM XML / Overpass (place/bbox); caching.
- `mapmatch/hmm.py`: Candidate generation (STRtree), emission/transition, Viterbi, fallback logic.
- `resample/road_resample.py`: Initial road-based resampling along polylines.
- `resample/minute_resample.py` (inside resample package): time-based resample.
- `features/semantics.py`: stub for semantic features (not used).
- `__init__.py`: package marker.

## Notes / gaps (current code)
- Inference (serverless-sim) for `curv_step` projects Δs along last heading; no step-wise snap-to-road in inference_service.
- Road-aware GRU with snap-after-each-step is not implemented.
- Per-horizon metrics exist in code but not rendered as tables/reports automatically.

## Experiment toggles (env flags)

These are optional and backward-compatible; unset = old behavior.

- `TDRIVE_CURVSTEP_WEIGHTED_LOSS=1`  
  curv_step loss uses step weights `[1,1,1,1,0.8,0.8,0.8,0.8,0.7,0.7]` (FDE less dominant).
- `TDRIVE_CURVSTEP_HIGH_SS=1`  
  scheduled sampling cap for curv_step increases to 0.8 (`ss_prob = min(0.8, 0.1*epoch)`).
- `TDRIVE_USE_GRAPH_CONTEXT_FEATURES=1` (prepare Phase B)  
  add `node_degree`, `is_junction` features (degree ≥3 → junction) to feature_cols/meta. If off, Phase B feature set stays the same.
- `TDRIVE_GRAPHML_PATH=/abs/path/to/beijing_taxid.graphml` (inference)  
  if Phase B + curv_step, inference_service rolls out Δs snapped per-step on the road graph; otherwise falls back to heading-based rollout.

### Preset combos (curv_step)

1) Baseline: no flags.  
2) Weighted: `TDRIVE_CURVSTEP_WEIGHTED_LOSS=1`.  
3) Weighted + high SS: `TDRIVE_CURVSTEP_WEIGHTED_LOSS=1`, `TDRIVE_CURVSTEP_HIGH_SS=1`.  
4) Weighted + node_degree: prepare with `TDRIVE_USE_GRAPH_CONTEXT_FEATURES=1`, train with (2) or (3).
# tdrive_predictor Developer Notes

This doc explains how the current code prepares data, trains, evaluates models, supported model modes, and what each file in `tdrive_predictor/` does.

## Quick commands (from `predict-model-with-taxi`)

```bash
# Phase A (free-space)
python -m tdrive_predictor.cli prepare --tdrive-root "./T-drive Taxi Trajectories/release/taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts/phase_a
python -m tdrive_predictor.cli train   --data-dir tdrive_predictor_artifacts/phase_a --mode xy --lookback 20
python -m tdrive_predictor.cli eval    --data-dir tdrive_predictor_artifacts/phase_a --mode xy

# Phase B (OSM/HMM)
python -m tdrive_predictor.cli prepare --tdrive-root "./T-drive Taxi Trajectories/release/taxi_log_2008_by_id" --num-taxis 5000 --max-idle-gap-min 15 --use-osm --graphml ./osm/beijing_taxid.graphml --cand-radius-m 150 --k-candidates 8 --beam-size 20 --road-resample --out-dir tdrive_predictor_artifacts/phase_b_5k_fast
python -m tdrive_predictor.cli train   --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --lookback 20 --epochs 80 --batch-size 256 --hidden-size 512 --target-scale 1.0 --early-stop-patience 6 --early-stop-min-delta 0.1 --device cuda --num-workers 16
python -m tdrive_predictor.cli eval    --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --graphml ./osm/beijing_taxid.graphml
```

## Pipeline: prepare → train → eval

### Prepare (Phase A vs Phase B)

- **Input**  
  Raw logs `taxi_id, timestamp, lon, lat` từ `T-drive Taxi Trajectories/release/taxi_log_2008_by_id/`.  
  Được đọc bằng `load_raw_tdrive()` trong `prepare.py`:
  - Lấy danh sách file `*.txt` theo ID taxi.
  - Đọc từng dòng, parse 4 cột, đưa vào DataFrame `df[taxi_id, ts, lon, lat]`.
  - Sort theo `(taxi_id, ts)` và bỏ trùng timestamp.

- **Phase A (free-space)** — `_prepare_phase_a(...)`
  - **WGS84 → UTM 50N**: `_compute_xy(df)` gọi `wgs84_to_utm()` để thêm cột `x, y` (mét, EPSG:32650).
  - **Segment trips với `--max-idle-gap-min`**: `segment_trips(df, max_idle_gap)` tạo `trip_id` mới khi khoảng cách thời gian giữa 2 điểm liên tiếp > idle gap.
  - **Resample 1 phút & nội suy**: `_resample_trip_minutely(trip_df)` tạo lưới thời gian 60s, reindex, nội suy `x,y` trên lưới đó.
  - **Tính feature**: `build_minutely_features_phase_a(...)` cho từng trip:
    - Vận tốc/tăng tốc: `dx, dy, dt, dist = hypot(dx,dy)`, `v = dist/dt`, `delta_v`, `a = delta_v/dt`.
    - Hướng: `heading = heading_from_dxdy(dx,dy)`, `delta_heading` wrap về [-π, π].
    - Cờ dừng & dwell: `stop_flag = 1(v < 0.5 m/s)`, `dw_time` cộng dồn khi dừng.
    - Thời gian: `tod_sin/cos` (time-of-day), `dow_sin/cos` (day-of-week), `rush_hour`.
  - **Split theo ngày (train/val/test)**: `train_val_test_split_by_day(df)` chia theo `ts.dt.date` (2–6 Feb → train, 7 → val, 8 → test cho năm 2008).

- **Phase B (OSM/HMM)** — `prepare_phase_b(...)`
  - **Map-match từng GPS lên road graph (HMM)**:
    - Load graph bằng `osm.loader.load_graph(...)` từ GraphML/XML/place/bbox.
    - Tạo `CandidateGenerator(G, radius, k, ...)` (STRtree tìm điểm candidate trên đường).
    - Tạo `HMMMapMatcher(G, cand, sigma_gps, ...)`:
      - Emission: Gaussian theo khoảng cách từ điểm tới candidate.
      - Transition: penalize theo chiều dài đường đi vs Δt/vmax, có thể dùng shortest-path (`--use-shortest-path`) và `turn_penalty`.
      - Viterbi + fallback cho các đoạn không có candidate.
  - **Footpoints & resample per minute**:
    - Với mỗi trip: lấy toạ độ chân điểm trên đường `foot_xy` cho từng quan sát.
    - Tạo DataFrame `[taxi_id, trip_id, ts, x_foot, y_foot]`, gọi `_resample_trip_minutely` giống Phase A nhưng trên tọa độ road.
    - Nếu bật `--road-resample`, sử dụng thêm logic trong `resample/road_resample.py` để resample theo chiều dài đường (curvilinear) dọc polyline.
  - **Feature set**: giống Phase A (v, a, delta_v, delta_heading, stop_flag, dw_time, tod_sin/cos, dow_sin/cos, rush_hour), nhưng `x,y` là toạ độ trên mạng đường.
  - **Split theo trip**: dùng `train_val_test_split_by_day` nhưng quan tâm `trip_id`, đảm bảo mỗi trip nằm trọn trong một split.

- **Outputs** (trong `out-dir`) — chung cho Phase A/B
  - `train.pkl`, `val.pkl`, `test.pkl`:
    - DataFrame đã chuẩn hoá, mỗi dòng là 1 bước thời gian với toàn bộ feature + mục tiêu dự báo.
  - `scaler.pkl`:
    - Dict `{feature: (mu, sigma)}` học trên train, dùng để z-score normalize train/val/test.
  - `meta.json`:
    - `feature_cols`, `lookback_default`, `phase`, `horizons_min`.
    - Phase B thêm: HMM params (sigma_gps, candidate_radius, k_candidates, beam_size, turn_penalty, use_shortest_path, use_road_resample), `graph_source`, `match_fallback_ratio`, v.v.
  - (Checkpoint model được lưu ở bước **Train**, không phải trong `prepare.py`.)

**Key HMM params** (Phase B):
- `--cand-radius-m`: bán kính tìm candidate quanh điểm GPS (m).
- `--k-candidates`: số candidate tối đa mỗi điểm.
- `--beam-size`: beam width cho Viterbi (giới hạn số state giữ lại mỗi bước).
- `--sigma-gps-m`: std của lỗi GPS cho emission Gaussian (m).
- `--turn-penalty`: phạt khi đổi hướng/edge, khuyến khích đường đi mượt.
- `--use-shortest-path`: dùng shortest-path thay vì Euclid khi tính transition.
- `--road-resample`: bật resampling dọc polyline (curvilinear).

### Train

- **Hàm chính**: `tdrive_predictor.train.train_gru(data_dir, ..., mode, ...)`.

1. **Đọc dữ liệu & meta**

```python
train_df = pd.read_pickle(os.path.join(data_dir, "train.pkl"))
val_df   = pd.read_pickle(os.path.join(data_dir, "val.pkl"))
meta     = pd.read_json(os.path.join(data_dir, "meta.json"), typ="series").to_dict()
feature_cols = meta["feature_cols"]
```

2. **Chọn Dataset theo `mode`** (sử dụng `tdrive_predictor.dataset`)

- `mode == "xy"` → `SequenceHorizonDataset`:
  - Input: chuỗi feature `[B, L, F]` (lookback L), target: dx, dy cho 4 horizon.
- `mode == "curv"` → `SequenceHorizonCurvDataset`:
  - Target: ds (curvilinear distance) cho horizon [1,3,5,10].
- `mode == "curv_step"` → `SequenceStepCurvDataset`:
  - Target: chuỗi ds với length 10 (10 bước, mỗi bước 1 phút).

3. **DataLoader**

```python
dl_train = DataLoader(
    ds_train,
    batch_size=batch_size,
    shuffle=True,
    num_workers=num_workers,
    pin_memory=(device == "cuda"),
)
dl_val = DataLoader(
    ds_val,
    batch_size=batch_size,
    shuffle=False,
    num_workers=num_workers,
    pin_memory=(device == "cuda"),
)
```

4. **Chọn model theo `mode`** (xem `tdrive_predictor.model`)

- `xy` → `GRUDisplacement(input_size=len(feature_cols), hidden_size=hidden_size, ...)`  
  GRU encoder + MLP head → vector 8 chiều (4 horizon × 2: dx, dy).
- `curv` → `GRUDisplacementRoad(input_size=len(feature_cols), hidden_size=max(hidden_size, 256), ...)`  
  GRU encoder + MLP head → 4 giá trị ds (horizon [1,3,5,10]).
- `curv_step` → `GRUStepDecoderRoad(input_size=len(feature_cols), hidden_size=max(hidden_size, 256), max_steps=10, ...)`  
  Encoder GRU lấy hidden cuối; decoder GRUCell + MLP chạy 10 bước để sinh ds_t từng phút.

5. **Loss & weighting**

- Loss cơ bản: `nn.SmoothL1Loss(reduction="none")`.
- Trọng số horizon:
  - `xy`: vector 8 chiều (cặp (dx, dy) cho mỗi horizon).
  - `curv`: `[1.0, 0.5, 0.5, 1.0]` (ưu tiên h1,h10 hơn h3,h5).
  - `curv_step`: `torch.ones(10)`.
- Nếu `target_scale != 1` (ví dụ 100.0), loss được tính trên mục tiêu đã scale:

```python
if target_scale and target_scale != 1.0:
    loss_elem = loss_fn(y_pred * target_scale, y_target * target_scale) * horizon_weights
else:
    loss_elem = loss_fn(y_pred, y_target) * horizon_weights
loss = loss_elem.mean()
```

6. **Scheduled sampling**

- Với `mode == "curv_step"`:

```python
ss_p = min(0.5, 0.1 * epoch)  # tăng dần lên 0.5
y_pred = model(x_seq, teacher=y_target, ss_prob=ss_p)
```

`GRUStepDecoderRoad` bên trong dùng `ss_prob` để mix giữa output bước trước và ground-truth ds khi feed cho bước kế.

- Với `mode == "curv"`:
  - Không có decoder, nhưng có “scheduled sampling surrogate”: trộn target với prediction trong loss để giảm exposure bias.

7. **Training loop**

- Với mỗi batch `x_seq, y_target, base_pos`:
  - Bỏ qua batch có NaN trong input/target.
  - Chuyển lên `device`, `opt.zero_grad()`.
  - Forward:
    - `curv_step`: gọi model với `teacher` & `ss_prob` như trên.
    - `xy/curv`: `y_pred = model(x_seq)`.
  - Tính loss (kết hợp weighting + scheduled sampling nếu có).
  - `loss.backward()`, clip gradient `max_norm=1.0`, `opt.step()`.
- In log mỗi epoch:

```text
[Epoch e/E] train_loss=... val_loss=... best_val=... lr=...
```

8. **Validation, LR schedule, early stopping**

- Sau mỗi epoch:
  - Eval trên `dl_val` với `torch.no_grad()`; với `curv_step` dùng `teacher=None, ss_prob=1.0` (pure autoregressive).
  - `scheduler.step(val_loss)` (`ReduceLROnPlateau`) để giảm LR khi val không giảm.
  - Nếu `val_loss < best_val - early_stop_min_delta`:
    - Cập nhật `best_val`, reset `no_improve`, lưu checkpoint.
  - Ngược lại tăng `no_improve`, nếu ≥ `early_stop_patience` thì dừng sớm.

9. **Checkpoint**

- Tên file theo mode:
  - `xy`   → `gru_phase_a.pt`
  - `curv` → `gru_phase_curv.pt`
  - `curv_step` → `gru_phase_curv_step.pt`
- Nội dung checkpoint:

```python
{
  "model_state": model.state_dict(),
  "meta": meta,
  "feature_cols": feature_cols,
  "lookback": lookback,
  "mode": mode,
  "hidden_size": hidden_size,
}
```

### Eval

- **Hàm**: `tdrive_predictor.evaluate.evaluate_gru(...)` (xy/curv) và `_evaluate_curv_step(...)` (curv_step).
- **Flow chung**:
  1. Load `meta`, `test.pkl`, `feature_cols`, chọn đúng model theo `mode` và load `model_state`.
  2. Sinh các cửa sổ (window) giống như trong training (lookback L, horizons).
  3. Chạy model để lấy dx, dy hoặc ds.
  4. Nếu có `--graphml` (curv/curv_step):
     - Dùng graph + đường polyline để chuyển ds thành (x,y) trên mạng đường.
     - Nếu không có graph: gom ds dọc theo polyline hoặc trong inference online thì kéo thẳng theo hướng cuối (heading).
  5. Ghép tất cả prediction/target thành tensor `preds_t`, `targets_t` (shape [B,8] → [B,4,2]) và tính metric bằng `metrics.py`:
     - `ADE`, `FDE` từ `compute_errors_m`.
     - `Hit@100/200/400` từ `hit_at_r` (final only).
     - Per-horizon error & Hit@200 từ `per_horizon_errors_m` và `per_horizon_hit_at_r`.
  6. In ra console và trả dict kết quả (dùng cho log/paper).
