# Research Paper: Predictive Digital Twin Replica Placement via User Mobility Forecasting

## Target Venue
IEEE Internet of Things Journal

## Core Problem
Serverless edge computing gây ra **cold start latency** khi container chưa được khởi tạo sẵn. Với DT (Digital Twin) services, user di động liên tục làm cho việc reactive placement không kịp — request đến edge node trước khi replica được warm up.

## Proposed Solution
Framework **proactive replica placement** kết hợp:
1. **Trajectory prediction** dự đoán vị trí user tương lai
2. **Service probability map** ánh xạ xác suất user sẽ query edge nào
3. **Online scheduler** phân bổ replica trước khi request đến, ưu tiên warm container

## System Architecture (Fig. 1)
End Users → Edge Cloudlets → Central Layer
├── Scheduler (online)
├── Deep Mobility Predictor (GRU-based)
├── Service Probability Map
├── Controller
└── Container Reuse (warm/cold lifecycle)

## Key Technical Components

### Mobility Predictor
- Model: `GRUStepDecoderRoad` — encoder-decoder với single-layer GRU (H=256)
- Input: GPS traces đã qua map-matching (OSM), kinematic features (CTRV-EKF)
- Training: SmoothL1 loss, Adam lr=1e-3, dropout p=0.1, scheduled sampling 0→0.5
- Baseline so sánh: CTRV-EKF (classical), free-space deep models, road-constrained models

### Evaluation Metrics
- **ADE** (Average Displacement Error), **FDE** (Final Displacement Error), **Hit@K**
- Phase A: free-space evaluation protocol
- Phase B: road-constrained evaluation protocol
- ⚠️ Cross-phase comparison là **invalid** — phải ghi rõ trong prose

### Scheduler
- Online algorithm, capacity-aware
- Tối ưu warm container reuse để tránh cold start chain
- Energy model: static + dynamic + network + cold start components

## Dataset
- **T-Drive Beijing Taxi** (KDD 2010/2011)
- GPS traces của taxi Bắc Kinh, dùng cho trajectory replay trong simulator