# T‑Drive Predictor — Phase A/B Updates Report

This document summarizes the changes just implemented for the T‑Drive predictor to support Phase B (OSM + map‑matching + on‑road prediction) while keeping Phase A (free‑space Δx,Δy) intact. It includes what changed, why, how to run, and what’s next.

## 1) Mục tiêu & Phạm vi
- Phase A: Chuẩn hóa dữ liệu T‑Drive theo phút, đặc trưng động học/thời gian, mô hình GRU dự báo Δx,Δy cho các horizon 1/3/5/10 phút.
- Phase B: Thêm OSM + HMM map‑matching, resample dọc đường (curvilinear), dataset “curv” (Δs), model GRU‑Δs, đánh giá topo‑aware và xuất CSV chẩn đoán.

Kỳ vọng chất lượng (OKR):
- FDE@10′ GRU‑Δs giảm ≥30% vs GRU‑Δxy (Phase A).
- Hit@200m tăng ≥+10 điểm phần trăm.
- CTRV‑snap‑topo thắng CTRV thường ~10–15% FDE@10′.

## 2) Tổng quan thay đổi theo file
- Data prep
  - `tdrive_predictor/prepare.py`
    - Phase A: logs rõ ràng; fix import time.
    - Phase B: loader OSM, HMM map‑matching; resample dọc đường; giữ `edge,s,edge_len`; tính `s_glob` (mét tích lũy theo quãng đường); lưu `graph.meta.json` và `match_fallback_ratio` trong `meta.json`.
- Resample dọc đường
  - `tdrive_predictor/resample/road_resample.py`: nội suy curvilinear theo `s` trên cùng edge; stitch qua edges kề; fallback XY; điền lại `s` bằng project khi thiếu.
- Dataset
  - `tdrive_predictor/dataset.py`: giữ `SequenceHorizonDataset` (Δx,Δy) và thêm `SequenceHorizonCurvDataset` (Δs_glob).
- Model
  - `tdrive_predictor/model.py`: giữ `GRUDisplacement` (Δx,Δy) và thêm `GRUDisplacementRoad` (Δs, hidden=256).
- Train
  - `tdrive_predictor/train.py`: thêm `--mode {xy,curv}`; target scaling; ReduceLROnPlateau; grad clip; “scheduled sampling surrogate” cho curv (trộn teacher/self trong loss, p ramp 0→0.5 ở 5 epoch đầu). Lưu ckpt `gru_phase_a.pt`/`gru_phase_curv.pt`.
- Eval
  - `tdrive_predictor/evaluate.py`: thêm `--mode {xy,curv}`; cho `curv`:
    - Nếu có đồ thị (`--graphml/--place/--bbox`): rollout Δs trên topology (greedy alignment theo tangent) để ra (Δx,Δy) rồi tính ADE/FDE/Hit@R.
    - Nếu không: fallback clip theo polyline GT (kiểm thử nhanh).
    - Xuất CSV per‑horizon (`per_horizon_curv.csv` cho curv, `per_horizon_xy.csv` cho xy), và slices (xy): `slices_speed_xy.csv`, `slices_stop_xy.csv`.
- CLI
  - `tdrive_predictor/cli.py`: thêm cờ `--mode` cho train/eval, và `--graphml/--place/--bbox` cho eval topo curv.
- Tài liệu nhanh
  - `predict-model-with-taxi/QUICKSTART-PhaseB.md`: hướng dẫn prepare/train/eval Phase B, flags HMM, CSV outputs.

## 3) Dữ liệu: Phase A vs Phase B
- Phase A (free‑space)
  - Resample thời gian 60s; không map‑matching; đặc trưng: v, a, delta_heading, stop_flag, dw_time, tod/dow/rush.
  - Split theo ngày (2–6 train, 7 val, 8 test). Lưu scaler + meta.
- Phase B (trên đường)
  - Loader OSM (GraphML ưu tiên; XML/place/bbox fallback). HMM map‑matching (beam/turn/speed; adaptive radius tuỳ chọn).
  - Resample dọc polyline (curvilinear) + stitching qua edges; giữ `edge`, `s`, `edge_len`; tính `s_glob`.
  - Lưu `graph.meta.json` (CRS, nguồn, bbox, #nodes/edges) và `match_fallback_ratio` trong `meta.json`.

## 4) Dataset & Targets
- Δx,Δy (Phase A): `SequenceHorizonDataset`
  - Input: `x_seq[L,F]`, Targets: 8 giá trị `[dx1,dy1, dx3,dy3, dx5,dy5, dx10,dy10]`.
- Δs (Phase B): `SequenceHorizonCurvDataset`
  - Input: `x_seq[L,F]`, Targets: 4 giá trị `[Δs1, Δs3, Δs5, Δs10]` dựa trên `s_glob`.
  - Mục tiêu: dự báo quãng đường dọc mạng đường; khi eval, quy đổi lại (Δx,Δy) bằng traversal theo đồ thị.

## 5) Kiến trúc & Huấn luyện
- GRU‑Δxy: `GRUDisplacement(input=F → 8)`
- GRU‑Δs: `GRUDisplacementRoad(input=F → 4)` (hidden=256)
- Loss/Recipe
  - SmoothL1 + trọng số horizon: Δxy → `[1,1,.5,.5,.5,.5,1,1]`, Δs → `[1,.5,.5,1]`.
  - Target scaling S=100; ReduceLROnPlateau(factor=0.5, patience=2); clip_grad=1.0.
  - Surrogate scheduled sampling cho curv: trộn target/pred trong loss (0.2) với p tăng 0→0.5 (5 epoch đầu).

## 6) Đánh giá & Xuất CSV
- Metrics chính: ADE/FDE + Hit@100/200/400 và per‑horizon.
- Eval curv (topo)
  - Nếu có đồ thị: khởi từ (edge,s) hiện tại, đi dọc edge, khi hết thì chọn neighbor edge theo hướng tiếp tuyến (greedy alignment), cho đến khi hết Δs ở mỗi horizon.
  - Fallback: clip dọc polyline GT (chỉ phục vụ kiểm thử).
- CSV
  - `per_horizon_curv.csv` hoặc `per_horizon_xy.csv`.
  - Slices (xy): `slices_speed_xy.csv` theo terciles vận tốc; `slices_stop_xy.csv` theo stop_flag.

## 7) CLI & Cách chạy
- Prepare Phase B (khuyến nghị có GraphML):
```
python -m tdrive_predictor.cli prepare \
  --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" \
  --num-taxis 50 --max-idle-gap-min 15 \
  --use-osm --graphml predict-model-with-taxi\osm\beijing_taxid.graphml \
  --road-resample --out-dir tdrive_predictor_artifacts\phase_b
```
- Train GRU‑Δs:
```
python -m tdrive_predictor.cli train \
  --data-dir tdrive_predictor_artifacts\phase_b --mode curv \
  --lookback 20 --epochs 20 --batch-size 64 --hidden-size 256
```
- Eval GRU‑Δs (topology rollout + CSV):
```
python -m tdrive_predictor.cli eval \
  --data-dir tdrive_predictor_artifacts\phase_b --mode curv \
  --graphml predict-model-with-taxi\osm\beijing_taxid.graphml
```
- Baselines:
```
# CTRV với snap topo
python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_b \
  --snap --snap-mode step-topo --graphml predict-model-with-taxi\osm\beijing_taxid.graphml

# Markov theo đoạn đường
python -m tdrive_predictor.cli eval-markov --data-dir tdrive_predictor_artifacts\phase_b \
  --graphml predict-model-with-taxi\osm\beijing_taxid.graphml
```

## 8) Mặc định khuyến nghị (HMM/OSM)
- `--cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12 --beam-size 10`.
- Ưu tiên GraphML (tải nhanh, reproducible). Nếu tải online: cân nhắc `--overpass-endpoint` và `--overpass-timeout`.
- Theo dõi `match_fallback_ratio` trong `meta.json` (mục tiêu < 5%).

## 9) Troubleshooting
- NaN trong train: dataset hiện lọc bỏ window có NaN; ensure prepare đã điền đầy đủ và scaler áp dụng đúng.
- Không có đồ thị khi eval curv: thêm `--graphml` (khuyến nghị) hoặc `--place/--bbox`. Nếu không, eval sẽ fallback clip polyline.
- Hiệu năng OSMnx: ưu tiên GraphML; XML lớn có thể chậm; giới hạn bbox.

## 10) Kế hoạch tiếp
- Decoder step‑per‑step (1′) cho GRU‑Δs + scheduled sampling “đúng nghĩa” và snap‑per‑step topo (ổn định rollout xa).
- Ranking đoạn → phân phối `P[i][j]^{t+h}` + calibration/EMA; benchmark end‑to‑end.
- Slice nâng cao: theo khoảng cách tới nút giao (degree≥3), theo gap gốc Δt, CDF FDE và overlay quỹ đạo.

---
Cần thêm ranking cloudlet hay decoder 1′ trước? Hãy cho biết để mình ưu tiên.
