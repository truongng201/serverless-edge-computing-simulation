# T-Drive Phase B — Quickstart (OSM + HMM Map-Matching)

This guide runs the map-matching pipeline using OSM, then trains/evaluates the same models on road-aligned data.

## 1) Install extra dependencies

Inside your virtual environment:

```powershell
pip install osmnx shapely networkx
# If wheels fail, try specific versions:
# pip install shapely==2.0.4 osmnx==1.9.3 networkx==3.2.1
```

## 2) Where to run and data location

- Run commands from: `predict-model-with-taxi`
- Raw data path: `T-drive Taxi Trajectories\release\taxi_log_2008_by_id`

## 3) Prepare data with map-matching

For a quick run, limit the area via `--bbox` to keep the graph small. BBox format is `(NORTH SOUTH EAST WEST)` in projected graph’s lat/lon space (osmnx handles projection internally).

Example (subset 30 taxis, 15‑minute idle gap):

```powershell
python -m tdrive_predictor.cli prepare `
  --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" `
  --num-taxis 30 `
  --max-idle-gap-min 15 `
  --use-osm `
  --place "Beijing, China" `
  --out-dir tdrive_predictor_artifacts\phase_b `
  --cand-radius-m 50 `
  --k-candidates 5 `
  --sigma-gps-m 12
```

Notes:
- You can use `--graphml predict-model-with-taxi\osm\beijing.graphml` to cache/load the graph.
- Use `--bbox N S E W` to restrict the area if needed.
- Set `--use-shortest-path` to enable graph shortest paths for transitions (slower but more faithful).
- To resample along roads (curvilinear) instead of time-only footpoints, add `--road-resample` in `prepare`.
- HMM tuning flags (optional, for quality/perf):
  - `--beam-size 10` (keep top-B candidates in Viterbi)
  - `--turn-penalty 0.1` (penalize turning in transitions)
  - `--speed-scale-mps 20` (scale for transition length penalty)
  - `--adaptive-radius A B MIN MAX` (r = clip(A + B*v, MIN, MAX), v in m/s)
- Offline option: if Overpass is unreliable, download a local OSM XML (e.g., from BBBike) that covers your bbox and build the graph offline:
  - `python -c "import osmnx as ox; G=ox.graph_from_xml('beijing.osm', bidirectional=True, simplify=True); G=ox.project_graph(G); ox.save_graphml(G, 'predict-model-with-taxi\\osm\\beijing_offline.graphml')"`
  - Then run prepare with `--graphml predict-model-with-taxi\osm\beijing_offline.graphml` or directly with `--xml beijing.osm`.

## 4) Train and evaluate (same as Phase A)

```powershell
python -m tdrive_predictor.cli train `
  --data-dir tdrive_predictor_artifacts\phase_b `
  --epochs 10 --lookback 20 --batch-size 64

python -m tdrive_predictor.cli eval `
  --data-dir tdrive_predictor_artifacts\phase_b
```

(Optional) CTRV baseline on Phase B data:
```powershell
python -m tdrive_predictor.cli eval-ctrv `
  --data-dir tdrive_predictor_artifacts\phase_b `
  --lookback 20
```

Markov baseline (requires OSM graph to map edges):
```powershell
python -m tdrive_predictor.cli eval-markov `
  --data-dir tdrive_predictor_artifacts\phase_b `
  --graphml predict-model-with-taxi\osm\beijing.graphml `
  --lookback 20
```

## 5) Troubleshooting

- Missing packages: install `osmnx`, `shapely`, `networkx` as above.
- Large graphs/slow HMM: use `--bbox` to limit area; reduce `--k-candidates` to 3; keep `--cand-radius-m` at 30–50.
- Shortest-path errors: if a pair of endpoints are disconnected, the matcher falls back to emission-only at that step.
- Fallbacks: when no candidates are found, the pipeline uses the original (x,y) for that time and continues.
