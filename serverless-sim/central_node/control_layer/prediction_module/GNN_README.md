# Hướng Dẫn ST-GNN (Spatial–Temporal Graph Neural Network)

Tài liệu này hướng dẫn setup môi trường, chạy huấn luyện/đánh giá ST‑GNN trên bộ dữ liệu DACT, và cách gọi mô hình đã huấn luyện trong mã Python.

## Yêu Cầu Môi Trường

- Python 3.8–3.11 (khuyến nghị 3.10)
- Gói Python tối thiểu:
  - `tensorflow` (hoặc `tensorflow-cpu`), `numpy`, `pandas`, `scikit-learn`, `seaborn`
  - Tùy chọn vẽ: `matplotlib`
- Lưu ý tương thích NumPy/TensorFlow:
  - Nếu gặp lỗi NumPy 2.x (ImportError/_ARRAY_API), dùng `--no-plot` khi chạy script, hoặc pin phiên bản:
    - `pip install "numpy<2" "tensorflow-cpu==2.12.*" pandas scikit-learn seaborn matplotlib`

## Dữ Liệu

- CSV mặc định: `serverless-sim/mock_data/DACT-Easy-Dataset.csv`
- Có thể đổi bằng tham số `--csv-path` khi chạy script.

## Chạy Nhanh (Smoke Test)

- Lệnh chạy nhanh (ít epoch, ít trip, tắt vẽ):
  - `python serverless-sim/central_node/control_layer/prediction_module/spatial_temporal_gnn/train_test.py --csv-path serverless-sim/mock_data/DACT-Easy-Dataset.csv --quick --no-plot`
- Mặc định `--quick`:
  - epochs=5, train_trips=6, test_trips=3, mô hình nhỏ 9 nút (3×3), không attention.

## Huấn Luyện Đầy Đủ (So Sánh Nhiều Cấu Hình)

- Chạy toàn bộ 5 cấu hình (Small/Medium/Medium+Attention/Large/Large+Attention):
  - `python serverless-sim/central_node/control_layer/prediction_module/spatial_temporal_gnn/train_test.py --csv-path serverless-sim/mock_data/DACT-Easy-Dataset.csv --no-plot`
- Tùy chọn hữu ích:
  - `--epochs 120` đổi số epoch
  - `--train-trips 30 --test-trips 20` đổi số trip train/test
  - `--no-plot` tắt vẽ nếu môi trường thiếu `matplotlib`

Kết quả lưu tại thư mục `spatial_temporal_gnn/` (file model `.keras`, đồ thị history `.png` nếu bật vẽ, và file tổng hợp so sánh `st_gnn_models_comparison.txt/png`).

## Cấu Hình Mặc Định Mô Hình

- File: `serverless-sim/central_node/control_layer/prediction_module/spatial_temporal_gnn/st_gnn_model.py`
- Tham số chính (có thể override trong `train_test.py`):
  - `sequence_length=10`, `input_features=33`, `output_features=2`
  - `num_spatial_nodes` ∈ {9,16,25} (3×3, 4×4, 5×5)
  - `gcn_units=[64,32]`, `lstm_units=[64,32]`, `dense_units=[64,32]`
  - `use_temporal_attention` True/False, `attention_units=64`
  - `dropout_rate=0.3`, `recurrent_dropout=0.2`, `l2_regularization=0.001`
  - `learning_rate=1e-3`, `batch_size=32`, `epochs` tuỳ chọn, `patience=20`

## Gọi Mô Hình Đã Huấn Luyện (Inference)

Bạn có thể nạp và gọi mô hình ST‑GNN bằng class `SpatialTemporalGNNModel`:

```python
import os
import numpy as np
from spatial_temporal_gnn.st_gnn_model import SpatialTemporalGNNModel
from data.enhanced_data_loader import EnhancedDACTDataLoader

# 1) Chuẩn bị dữ liệu test (tạo chuỗi đặc trưng 33 chiều)
csv_path = 'serverless-sim/mock_data/DACT-Easy-Dataset.csv'
loader = EnhancedDACTDataLoader(csv_path=csv_path, sequence_length=10)
data = loader.prepare_for_training(train_count=5, test_count=2)

X_test = data['X_test']   # shape: [N, 10, 33]
y_test = data['y_test']   # shape: [N, 2] (tọa độ chuẩn hoá)
bounds = data['bounds']   # dùng để giải chuẩn hoá lat/lng

# 2) Nạp mô hình đã train (.keras)
model_path = os.path.join('serverless-sim', 'central_node', 'control_layer', 'prediction_module',
                          'spatial_temporal_gnn', 'st-gnn_small_9_nodes_model.keras')

model = SpatialTemporalGNNModel()  # cấu hình sẽ được load từ file keras
model.load_model(model_path)

# 3) Dự đoán
y_pred = model.predict(X_test)  # [N, 2] toạ độ chuẩn hoá (lat_norm, lng_norm)

# 4) Giải chuẩn hoá về lat/lng (đơn giản)
lat_span = bounds['lat_max'] - bounds['lat_min']
lng_span = bounds['lng_max'] - bounds['lng_min']
lat = y_pred[:, 0] * lat_span + bounds['lat_min']
lng = y_pred[:, 1] * lng_span + bounds['lng_min']
print('Pred sample lat/lng:', lat[:3], lng[:3])
```

Ghi chú:
- Đầu vào `X` phải có shape `[batch, sequence_length, 33]`. Nếu gọi realtime, bạn cần tự tính đặc trưng 33 chiều cho 10 timestep gần nhất (có thể tái sử dụng công thức trong `EnhancedDACTDataLoader`).
- Nếu chỉ có (lat,lng) mà không tính đủ 33 đặc trưng, wrapper `TrajectoryPredictor` hiện tại chỉ hỗ trợ (x,y) đơn giản, không tương thích với ST‑GNN.

## Tích Hợp Runtime (Gợi Ý)

- Cách A (đề xuất, chính xác hơn):
  - Thu thập 10 điểm gần nhất (TimeStep), tính các đặc trưng 33 chiều theo công thức trong `EnhancedDACTDataLoader` (vận tốc/gia tốc/rolling/…)
  - Chuẩn hoá theo `bounds` đã học (lưu từ training). Gọi `model.predict()` như ví dụ trên.

- Cách B (nhanh nhưng đơn giản hơn):
  - Dùng `TrajectoryPredictor` (linear extrapolation hoặc một model nhỏ chỉ dùng (x,y)) nếu bạn không thể tính đủ 33 đặc trưng. Cần huấn luyện riêng model phù hợp input (x,y) cho wrapper này.

## Mẹo/Kiểm Tra Nhanh

- Kiểm tra pipeline nhanh: dùng `--quick --no-plot` để xác nhận training chạy OK.
- Nếu muốn chỉ chạy một biến thể (ví dụ Medium + Attention 16 nodes), chạy full và xem hàng tương ứng trong bảng so sánh; hoặc chỉnh script để lọc cấu hình mong muốn.

## Vấn Đề Thường Gặp

- Lỗi NumPy/Matplotlib: chạy với `--no-plot` hoặc pin `numpy<2`, `tensorflow-cpu==2.12.*`.
- CSV không tìm thấy: dùng `--csv-path` để chỉ đúng `serverless-sim/mock_data/DACT-Easy-Dataset.csv`.

