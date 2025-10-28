Setup

cd predict-model-with-taxi
Cài gói chung (Phase A): pip install -U pip && pip install numpy pandas pyproj torch tqdm
Cài thêm cho Phase B: pip install osmnx shapely networkx
Phase A (Free-Space)

Chuẩn bị (ví dụ 50 taxis):
    python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts\phase_a

Train GRU:
    python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_a --epochs 10 --lookback 20 --batch-size 64

Đánh giá GRU:
    python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_a

CTRV baseline (free-space):
    python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_a --lookback 20

Expected outcome:
    Sinh thư mục tdrive_predictor_artifacts\phase_a gồm: train.pkl, val.pkl, test.pkl, scaler.pkl, meta.json, và gru_phase_a.pt.
    Log train giảm dần; eval in ra ADE/FDE/Hit@R (mét). Với 50 taxis: ADE cỡ 700–900 m, FDE ~1–2 km, Hit@100 ~0.4–0.6 (mang tính tham khảo).
    Phase B (OSM + HMM)

Chuẩn bị (HMM map-matching; khuyến nghị cache graph):

Lần đầu (tải + cache):
    python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 30 --max-idle-gap-min 15 --use-osm --place "Beijing, China" --graphml predict-model-with-taxi\osm\beijing.graphml --out-dir tdrive_predictor_artifacts\phase_b --cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12

Lần sau (load từ cache, nhanh hơn):
    python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 30 --max-idle-gap-min 15 --use-osm --graphml predict-model-with-taxi\osm\beijing.graphml --out-dir tdrive_predictor_artifacts\phase_b --cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12

    Gợi ý tăng tốc: dùng --bbox N S E W để giới hạn khu vực (tùy chọn), giữ --k-candidates=3–5, --cand-radius-m=30–50.

    Tùy chọn chính xác hơn (chậm hơn): thêm --use-shortest-path.

Train/Eval GRU (trên Phase B):

    Train: python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_b --epochs 10 --lookback 20 --batch-size 64

    Eval: python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_b 

CTRV baseline (snap nhẹ theo road):
    python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_b --lookback 20 --snap --graphml predict-model-with-taxi\osm\beijing.graphml --cand-radius-m 30 --k-candidates 3

Markov baseline (trên segment, không semantics):
    python -m tdrive_predictor.cli eval-markov --data-dir tdrive_predictor_artifacts\phase_b --graphml predict-model-with-taxi\osm\beijing.graphml --lookback 20

Expected outcome:
    Sinh thư mục tdrive_predictor_artifacts\phase_b (tương tự Phase A).
    So với Phase A: thường thấy FDE giảm (10–30% tùy subset/params) và Hit@R tăng; log HMM chạy ổn (không crash), thời gian chuẩn bị dài hơn Phase A (tùy graph).
    CTRV với --snap thường tốt hơn CTRV free-space ở 5–10 phút.
    Markov baseline là mốc tham chiếu hành vi theo giờ; kết quả có thể kém ở 1–3 phút nhưng giúp so sánh tuyến tính theo giờ.
    Sanity Checks

Kiểm tra file artifacts tồn tại:
    dir tdrive_predictor_artifacts\phase_a và dir tdrive_predictor_artifacts\phase_b

Kiểm tra NaN sau prepare:
    python - << 'PY' (hoặc tạo file nhỏ)
    import pandas as pd; df=pd.read_pickle('predict-model-with-taxi/tdrive_predictor_artifacts/phase_b/train.pkl'); print('rows',len(df),'nans',int(df.isna().sum().sum()))
    Dataset size > 0 (train/val/test không rỗng), loss hữu hạn, metrics không NaN.
Notes
    Nếu gặp lỗi osmnx/shapely: đảm bảo pip install osmnx shapely networkx ok (Windows cần wheels phù hợp).
    Nếu prepare Phase B chậm: dùng --bbox, giảm --k-candidates, giữ --cand-radius-m đúng khu vực đô thị.
    Road-resample hiện ở mức “footpoint + nội suy theo thời gian” (giữ liên tục). Có thể nâng cấp dần sang nội suy curvilinear khi cần.




python -m tdrive_predictor.cli train `
  --data-dir tdrive_predictor_artifacts\phase_a `
  --epochs 10 `
  --lookback 20 `
  --batch-size 64
Training (50 taxis, 10 epochs): best val loss ≈ 440.6; stable convergence.
Test metrics (UTM meters): ADE ≈ 768.7; FDE ≈ 1526.9; Hit@100/200/400 ≈ 0.512/0.518/0.530.
Reading: many near hits (≤100 m), but long-tail errors inflate FDE (no road constraints).
Limitations: free-space prediction; no map-matching/snap or road semantics yet.
Next: add CTRV baseline; Phase B HMM map-matching + per-step snap; road-aware GRU and ablations.