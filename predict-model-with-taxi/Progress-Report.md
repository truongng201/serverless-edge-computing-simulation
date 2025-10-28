# Progress Report — T-Drive Prediction (Phase A/B)

Date: 2025-10-22

## 1) Overview
Dự án xây dựng pipeline dự báo tọa độ tương lai (1/3/5/10 phút) cho dữ liệu T‑Drive. Hiện đã hoàn thiện Phase A (free‑space) và triển khai một phần Phase B (OSM + HMM map‑matching), kèm các baseline để so sánh.

## 2) Đã Hoàn Thành (Running)
- Phase A (free‑space, chạy ổn định)
  - Đọc dữ liệu T‑Drive, WGS84 → UTM Zone 50N (mét), cắt trip theo `--max-idle-gap-min` (mặc định 15’), lọc outlier tốc độ >160 km/h.
  - Resample đều mỗi 60s (giữ mốc gốc bằng union index → nội suy theo thời gian), tạo đặc trưng động học + thời gian, chia ngày (train=2–6, val=7, test=8), chuẩn hóa theo train.
  - GRU Δx/Δy (L=20, hidden=128, SmoothL1 có trọng số) + CLI prepare/train/eval.
  - Fixes: loại NaN do resample, sửa `dw_time` (tránh lỗi index), tránh tạo path lồng nhau, luôn lưu checkpoint.

- Baselines
  - CTRV (EKF) không cần huấn luyện: dự báo Δx/Δy ở {1,3,5,10}, đã có CLI `eval-ctrv` (Phase A/B).
  - Markov trên segment (không semantics): đã thêm, dùng hour‑conditioned transitions, rollout theo phút (Phase B data khuyến nghị).

- Phase B (map‑matching — partial)
  - OSM loader: load/cache GraphML, project CRS; hỗ trợ `--bbox/--place`, `--graphml`, `--overpass-endpoint`, `--overpass-timeout`.
  - HMM: CandidateGenerator (STRtree), Emission Gaussian theo khoảng cách, Transition theo khả thi (vmax·Δt), Viterbi + fallback.
  - Tích hợp `prepare --use-osm`: map‑match → lấy footpoints → resample 60s → đặc trưng/split như Phase A. (Resample theo “footpoint + time” đã chạy; resample curvilinear sẽ nâng cấp thêm.)

- Tài liệu
  - QUICKSTART-PhaseA.md, QUICKSTART-PhaseB.md (cách cài đặt/chạy), hướng dẫn sanity‑check.

## 3) Cách Chạy Nhanh
Chạy từ thư mục `predict-model-with-taxi`.

- Phase A
  - Prepare: `python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts\phase_a`
  - Train:   `python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_a --epochs 10 --lookback 20 --batch-size 64`
  - Eval:    `python -m tdrive_predictor.cli eval  --data-dir tdrive_predictor_artifacts\phase_a`
  - CTRV:    `python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_a --lookback 20`

- Phase B (khuyến nghị dùng bbox + cache GraphML)
  - Prepare (ví dụ bbox nội đô + mirror Overpass, timeout 600s):
    `python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 30 --max-idle-gap-min 15 --use-osm --bbox 39.95 39.90 116.45 116.35 --overpass-endpoint https://overpass.kumi.systems/api/interpreter --overpass-timeout 600 --graphml predict-model-with-taxi\osm\beijing_small.graphml --out-dir tdrive_predictor_artifacts\phase_b --cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12`
  - Train/Eval: giống Phase A nhưng `--data-dir tdrive_predictor_artifacts\phase_b`
  - CTRV snap: `python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_b --lookback 20 --snap --graphml predict-model-with-taxi\osm\beijing_small.graphml`
  - Markov:    `python -m tdrive_predictor.cli eval-markov --data-dir tdrive_predictor_artifacts\phase_b --graphml predict-model-with-taxi\osm\beijing_small.graphml --lookback 20`

## 4) Kết Quả Mẫu (Phase A, 50 taxis)
- Train loss giảm: ~483.6 → ~458.3; best val ≈ 440.6 (ổn định).
- Test: ADE ≈ 768.7 m; FDE ≈ 1526.9 m; Hit@100/200/400 ≈ 0.512/0.518/0.530.
- Nhận xét: nhiều điểm “trúng gần” (≤100 m) nhưng có đuôi lỗi xa (không ràng buộc đường). Phase B kỳ vọng giảm FDE, tăng Hit@R.

## 5) Vấn Đề Đã Gặp & Cách Khắc Phục
- NaN sau resample: giữ mốc gốc bằng union index → interpolate theo thời gian → ffill/bfill; bỏ batch chứa NaN/Inf khi train; luôn lưu checkpoint cuối.
- `dw_time` lỗi index: tính theo từng trip, tránh groupby.apply trả MultiIndex.
- Artifacts bị lồng path: chuẩn hóa default `--out-dir`/`--data-dir`.
- OSMnx API khác biệt: `graph_from_bbox` dùng `bbox=(N,S,E,W)` → đã tương thích nhiều phiên bản.
- Overpass timeout: thêm `--overpass-endpoint`, `--overpass-timeout`; khuyến nghị dùng bbox nhỏ + cache GraphML.

## 6) Còn Tồn Tại / Sẽ Làm Tiếp
- Resample dọc đường (curvilinear) hoàn chỉnh: nội suy theo s dọc polyline, xử lý chuyển segment, để thay thế nội suy giữa footpoints khi segment thay đổi.
- CTRV snap‑to‑road nâng cao: ưu tiên edge liên thông theo topo trong lúc snap horizons.
- Tối ưu HMM: beam pruning, giới hạn K/radius hợp lý, shortest‑path tùy chọn theo nhu cầu chính xác/hiệu năng.
- Đánh giá mở rộng: per‑horizon ADE/FDE/Hit@R, lát cắt theo gap thời gian, theo giờ trong ngày.
- (Tùy chọn) Tinh chỉnh GRU: scheduled sampling, HParam (hidden 256, L=30), lr scheduler.

## 7) Rủi Ro & Giảm Thiểu
- Overpass/OSM chậm hoặc timeout: dùng bbox nhỏ, mirror endpoint, tăng timeout, cache GraphML.
- Sai khác bản đồ (OSM hiện tại vs dữ liệu 2008): cho phép fallback free‑space; log tỷ lệ fallback để giám sát.
- Hiệu năng HMM: giảm K (3–5), radius (30–50 m), giới hạn phạm vi; bật shortest‑path khi đã ổn.

## 8) Danh Mục File Chính Đã Thêm/Sửa
- Pipeline & CLI: `tdrive_predictor/prepare.py`, `tdrive_predictor/cli.py`
- Model & Data: `tdrive_predictor/model.py`, `tdrive_predictor/dataset.py`, `tdrive_predictor/metrics.py`, `tdrive_predictor/utils.py`
- Baselines: `baselines/ctrv.py`, `baselines/markov.py`
- OSM/HMM: `osm/loader.py`, `mapmatch/hmm.py`, `resample/road_resample.py`
- Docs: `QUICKSTART-PhaseA.md`, `QUICKSTART-PhaseB.md`, file này `Progress-Report.md`

---
Ghi chú: Theo yêu cầu, bỏ phần semantics đường (lanes/maxspeed/highway). Khi Phase B ổn định trên subset, sẽ nâng cấp resample curvilinear và tinh chỉnh tham số HMM/GRU để đạt cải thiện rõ rệt về FDE/Hit@R.
