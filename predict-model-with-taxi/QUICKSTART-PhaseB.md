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
# QUICKSTART — Phase B (OSM + GRU-Δs)

This quickstart shows how to prepare Phase B data (map-matched + on-road resample), train the GRU-Δs model, and evaluate with topo-aware rollout and CSV diagnostics.

## 1) Prepare data (map-matching + road resample)

Recommended: use a cached GraphML for reproducibility and speed.

PowerShell (from `predict-model-with-taxi/`):

```
python -m tdrive_predictor.cli prepare \
  --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" \
  --num-taxis 50 --max-idle-gap-min 15 \
  --use-osm --graphml predict-model-with-taxi\osm\beijing_taxid.graphml \
  --road-resample --out-dir tdrive_predictor_artifacts\phase_b
```

Flags of interest:
- `--graphml` (preferred), or `--xml`, or `--place`/`--bbox NORTH SOUTH EAST WEST` (OSMnx download).
- HMM tuning: `--cand-radius-m` (40–50), `--k-candidates` (5), `--sigma-gps-m` (10–12), `--beam-size` (10–20), `--turn-penalty`, `--speed-scale-mps`.
- `--use-shortest-path` to use graph shortest-path length in transitions.
- `--adaptive-radius A B MIN MAX` to adapt candidate radius to speed.
- `--road-resample` to resample minutely along polylines (curvilinear) with stitching.

Outputs:
- `phase_b/train.pkl,val.pkl,test.pkl` with engineered features and columns `edge,s,edge_len,s_glob`.
- `phase_b/meta.json` (HMM params, thresholds) and `phase_b/graph.meta.json` (graph stats, bbox, CRS).

## 2) Train GRU-Δs (curv mode)

```
python -m tdrive_predictor.cli train \
  --data-dir tdrive_predictor_artifacts\phase_b \
  --mode curv --lookback 20 --batch-size 64 \
  --hidden-size 256 --num-layers 1 --dropout 0.1 \
  --epochs 20 --target-scale 100
```

Notes:
- Uses SmoothL1 + horizon weights [1, .5, .5, 1], ReduceLROnPlateau, grad clip.
- Includes a light scheduled-sampling surrogate that mixes teacher vs self outputs with p ramp 0→0.5 over first 5 epochs.
- Checkpoint: `gru_phase_curv.pt` in `data-dir`.

## 3) Evaluate (topology-aware rollout, CSV)

```
python -m tdrive_predictor.cli eval \
  --data-dir tdrive_predictor_artifacts\phase_b \
  --mode curv --graphml predict-model-with-taxi\osm\beijing_taxid.graphml
```

What it computes:
- ADE/FDE + Hit@100/200/400 and per-horizon metrics.
- Writes CSVs: `per_horizon_curv.csv` (mode=curv) or `per_horizon_xy.csv` (mode=xy), and simple slices for xy mode: `slices_speed_xy.csv`, `slices_stop_xy.csv`.

## 4) Baselines

- CTRV (EKF): `python -m tdrive_predictor.cli eval-ctrv --data-dir ... [--snap --graphml ... --snap-mode step-topo]`
- Markov (road segments): `python -m tdrive_predictor.cli eval-markov --data-dir ... --graphml ...`

## 5) Tips & Defaults

- Start with `--cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12 --beam-size 10`.
- If Overpass slow/unreliable, use `--graphml` or `--xml` offline.
- Monitor `match_fallback_ratio` in `meta.json`. Aim < 5%.

## Preset — 1k-accurate (slow, higher quality)

- Purpose: maximize map-matching fidelity and on-road rollout quality; expect long runtime.
- Graph: use cached GraphML; shortest-path transitions; larger candidate set and beam.

Prepare (SP=True, larger radius/beam/k, smaller sigma):

```powershell
python -m tdrive_predictor.cli prepare `
  --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" `
  --num-taxis 1000 `
  --max-idle-gap-min 15 `
  --use-osm --graphml .\osm\beijing_taxid.graphml `
  --cand-radius-m 200 --k-candidates 12 --beam-size 50 `
  --use-shortest-path --turn-penalty 0.3 --sigma-gps-m 8 `
  --road-resample `
  --out-dir tdrive_predictor_artifacts\phase_b_1k_sp
```

Optional (speed-aware candidate radius and transition scaling): add
`--adaptive-radius 10 3 50 250 --speed-scale-mps 18`.

Train (GRU Δs stepwise + early stop):

```powershell
python -m tdrive_predictor.cli train `
  --data-dir tdrive_predictor_artifacts\phase_b_1k_sp `
  --mode curv_step --lookback 20 --epochs 80 `
  --batch-size 64 --hidden-size 512 --target-scale 1.0 `
  --early-stop-patience 6 --early-stop-min-delta 0.1
```

Eval (topology-aware rollout on OSM):

```powershell
python -m tdrive_predictor.cli eval `
  --data-dir tdrive_predictor_artifacts\phase_b_1k_sp `
  --mode curv_step --graphml .\osm\beijing_taxid.graphml
```
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --use-osm --graphml .\osm\beijing_taxid.graphml --cand-radius-m 150 --k-candidates 8 --beam-size 20 --road-resample --out-dir tdrive_predictor_artifacts\phase_b
[Phase B] Segmented trips=1547 | max_idle_gap_min=15
[Phase B] Graph loaded | source=graphml
[Phase B] HMM params | sigma=12.0 | radius=150.0 | K=8 | beam=20 | turn_penalty=0.0 | sp=False | road_resample=True
[Phase B] Map-matching trips: 100%|██████████████████████████████████████████████████████████████████████████| 7643/7643 [01:25<00:00, 88.96it/s]
[Phase B] Split sizes | train=100957 val=15189 test=13116
[Phase B] Saved artifacts to tdrive_predictor_artifacts\phase_b | fallback_ratio=0.21592593115323275 | elapsed=126.5s
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> 

(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_b --mode curv --lookback 20 --epochs 20 --batch-size 64 --hidden-size 256
[Epoch 1/20] train_loss=38810.6737 val_loss=34233.8121 best_val=34233.8121 lr=1.00e-03
[Epoch 2/20] train_loss=28059.3071 val_loss=33686.0346 best_val=33686.0346 lr=1.00e-03
[Epoch 3/20] train_loss=27466.1521 val_loss=33345.7008 best_val=33345.7008 lr=1.00e-03
[Epoch 4/20] train_loss=27142.0406 val_loss=33013.4839 best_val=33013.4839 lr=1.00e-03
[Epoch 5/20] train_loss=26839.1420 val_loss=33168.0046 best_val=33013.4839 lr=1.00e-03
[Epoch 6/20] train_loss=26481.6508 val_loss=33006.8338 best_val=33006.8338 lr=1.00e-03
[Epoch 7/20] train_loss=26059.0752 val_loss=33569.6611 best_val=33006.8338 lr=1.00e-03
[Epoch 8/20] train_loss=25574.1415 val_loss=33605.1132 best_val=33006.8338 lr=1.00e-03
[Epoch 9/20] train_loss=24957.9924 val_loss=33589.8756 best_val=33006.8338 lr=5.00e-04
[Epoch 10/20] train_loss=23932.2944 val_loss=33883.7531 best_val=33006.8338 lr=5.00e-04
[Epoch 11/20] train_loss=23220.4812 val_loss=34299.8892 best_val=33006.8338 lr=5.00e-04
[Epoch 12/20] train_loss=22623.5582 val_loss=34676.2054 best_val=33006.8338 lr=2.50e-04
[Epoch 13/20] train_loss=21738.8345 val_loss=35075.0540 best_val=33006.8338 lr=2.50e-04
[Epoch 14/20] train_loss=21257.2110 val_loss=35287.9502 best_val=33006.8338 lr=2.50e-04
[Epoch 15/20] train_loss=20848.8302 val_loss=35534.9055 best_val=33006.8338 lr=1.25e-04
[Epoch 16/20] train_loss=20309.5998 val_loss=35773.5718 best_val=33006.8338 lr=1.25e-04
[Epoch 17/20] train_loss=20068.5806 val_loss=35858.6461 best_val=33006.8338 lr=1.25e-04
[Epoch 18/20] train_loss=19837.9128 val_loss=36091.7362 best_val=33006.8338 lr=6.25e-05
[Epoch 19/20] train_loss=19526.3610 val_loss=36137.3321 best_val=33006.8338 lr=6.25e-05
[Epoch 20/20] train_loss=19395.4371 val_loss=36178.0965 best_val=33006.8338 lr=6.25e-05
Saved checkpoint: tdrive_predictor_artifacts\phase_b\gru_phase_curv.pt

(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_b --mode curv --graphml .\osm\beijing_taxid.graphml
>>
Per-horizon mean error (m): {'h1': 387.57, 'h3': 695.68, 'h5': 1034.68, 'h10': 1850.95}
Per-horizon Hit@200: {'h1': 0.525, 'h3': 0.399, 'h5': 0.36, 'h10': 0.321}
{'ADE': 992.218, 'FDE': 1850.949, 'Hit@100': 0.27, 'Hit@200': 0.321, 'Hit@400': 0.351, 'PerHorizonError': {'h1': 387.56951904296875, 'h3': 695.6753540039062, 'h5': 1034.6790771484375, 'h10': 1850.9493408203125}, 'PerHorizonHit@200': {'h1': 0.5250265213617513, 'h3': 0.39945992863342655, 'h5': 0.359918989295014, 'h10': 0.32114958048027775}}
Metrics: {'ADE': 992.2183227539062, 'FDE': 1850.9493408203125, 'Hit@100': 0.2697463631629944, 'Hit@200': 0.3211495876312256, 'Hit@400': 0.35123926401138306, 'PerHorizonError': {'h1': 387.56951904296875, 'h3': 695.6753540039062, 'h5': 1034.6790771484375, 'h10': 1850.9493408203125}, 'PerHorizonHit@200': {'h1': 0.5250265213617513, 'h3': 0.39945992863342655, 'h5': 0.359918989295014, 'h10': 0.32114958048027775}}



(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_b --mode curv_step --lookback 20 --epochs 15 --batch-size 64 --hidden-size 256
[Epoch 1/15] train_loss=4824.0167 val_loss=13116.9116 best_val=13116.9116 lr=1.00e-03
[Epoch 2/15] train_loss=3379.6883 val_loss=13226.4911 best_val=13116.9116 lr=1.00e-03
[Epoch 3/15] train_loss=4529.0616 val_loss=12697.9535 best_val=12697.9535 lr=1.00e-03
[Epoch 4/15] train_loss=5669.4751 val_loss=12451.0965 best_val=12451.0965 lr=1.00e-03
[Epoch 5/15] train_loss=6913.9320 val_loss=12520.1543 best_val=12451.0965 lr=1.00e-03
[Epoch 6/15] train_loss=6854.5768 val_loss=12549.0196 best_val=12451.0965 lr=1.00e-03
[Epoch 7/15] train_loss=6879.3679 val_loss=12518.8574 best_val=12451.0965 lr=5.00e-04
[Epoch 8/15] train_loss=6791.7491 val_loss=12308.8667 best_val=12308.8667 lr=5.00e-04
[Epoch 9/15] train_loss=6726.3351 val_loss=12562.8209 best_val=12308.8667 lr=5.00e-04
[Epoch 10/15] train_loss=6684.8953 val_loss=12280.4384 best_val=12280.4384 lr=5.00e-04
[Epoch 11/15] train_loss=6667.0671 val_loss=12098.6222 best_val=12098.6222 lr=5.00e-04
[Epoch 12/15] train_loss=6679.2667 val_loss=12104.4976 best_val=12098.6222 lr=5.00e-04
[Epoch 13/15] train_loss=6597.9601 val_loss=12174.8256 best_val=12098.6222 lr=5.00e-04
[Epoch 14/15] train_loss=6645.0292 val_loss=11997.3162 best_val=11997.3162 lr=5.00e-04
[Epoch 15/15] train_loss=6613.6801 val_loss=12005.0799 best_val=11997.3162 lr=5.00e-04
Saved checkpoint: tdrive_predictor_artifacts\phase_b\gru_phase_curv_step.pt
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_b --mode curv_step --graphml .\osm\beijing_taxid.graphml                               
Metrics: {'ADE': 991.7742309570312, 'FDE': 1843.3043212890625, 'Hit@100': 0.2797762453556061, 'Hit@200': 0.33069726824760437, 'Hit@400': 0.35856881737709045, 'PerHorizonError': {'h1': 389.171142578125, 'h3': 693.8474731445312, 'h5': 1040.77392578125, 'h10': 1843.3043212890625}, 'PerHorizonHit@200': {'h1': 0.5236763429453177, 'h3': 0.4028353746745106, 'h5': 0.3649339376989102, 'h10': 0.3306972707107725}}
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> 






(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --use-osm --graphml .\osm\beijing_taxid.graphml --cand-radius-m 150 --k-candidates 8 --beam-size 20 --use-shortest-path --turn-penalty 0.2 --sigma-gps-m 10 --road-resample --out-dir tdrive_predictor_artifacts\phase_b_sp
>>
[Phase B] Segmented trips=1547 | max_idle_gap_min=15
[Phase B] Graph loaded | source=graphml
[Phase B] HMM params | sigma=10.0 | radius=150.0 | K=8 | beam=20 | turn_penalty=0.2 | sp=True | road_resample=True
[Phase B] Map-matching trips: 100%|████████████████████████████████████████████████████████████████████████| 7643/7643 [1:22:32<00:00,  1.54it/s]
[Phase B] Split sizes | train=100957 val=15189 test=13116
[Phase B] Saved artifacts to tdrive_predictor_artifacts\phase_b_sp | fallback_ratio=0.21592593115323275 | elapsed=4995.7s
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_b_sp --mode curv_step --lookback 20 --epochs 30 --batch-size 64 --hidden-size 256 --target-scale 1.0   
>>
[Epoch 1/30] train_loss=41.9588 val_loss=123.5965 best_val=123.5965 lr=1.00e-03
[Epoch 2/30] train_loss=32.2326 val_loss=120.7578 best_val=120.7578 lr=1.00e-03
[Epoch 3/30] train_loss=43.6281 val_loss=121.2958 best_val=120.7578 lr=1.00e-03
[Epoch 4/30] train_loss=56.2692 val_loss=119.6847 best_val=119.6847 lr=1.00e-03
[Epoch 5/30] train_loss=67.3433 val_loss=121.4231 best_val=119.6847 lr=1.00e-03
[Epoch 6/30] train_loss=66.2531 val_loss=118.7270 best_val=118.7270 lr=1.00e-03
[Epoch 7/30] train_loss=66.8053 val_loss=120.5407 best_val=118.7270 lr=1.00e-03
[Epoch 8/30] train_loss=65.6840 val_loss=117.7075 best_val=117.7075 lr=1.00e-03
[Epoch 9/30] train_loss=65.9465 val_loss=117.5545 best_val=117.5545 lr=1.00e-03
[Epoch 10/30] train_loss=65.3925 val_loss=118.2580 best_val=117.5545 lr=1.00e-03
[Epoch 11/30] train_loss=65.5283 val_loss=117.2623 best_val=117.2623 lr=1.00e-03
[Epoch 12/30] train_loss=65.4549 val_loss=118.3227 best_val=117.2623 lr=1.00e-03
[Epoch 13/30] train_loss=64.8758 val_loss=118.9730 best_val=117.2623 lr=1.00e-03
[Epoch 14/30] train_loss=65.9441 val_loss=116.7230 best_val=116.7230 lr=1.00e-03
[Epoch 15/30] train_loss=64.9886 val_loss=117.2964 best_val=116.7230 lr=1.00e-03
[Epoch 16/30] train_loss=64.7653 val_loss=116.5500 best_val=116.5500 lr=1.00e-03
[Epoch 17/30] train_loss=64.5657 val_loss=120.7788 best_val=116.5500 lr=1.00e-03
[Epoch 18/30] train_loss=64.8102 val_loss=116.5694 best_val=116.5500 lr=1.00e-03
[Epoch 19/30] train_loss=64.2642 val_loss=116.1028 best_val=116.1028 lr=1.00e-03
[Epoch 20/30] train_loss=64.7232 val_loss=116.6355 best_val=116.1028 lr=1.00e-03
[Epoch 21/30] train_loss=64.5678 val_loss=117.7454 best_val=116.1028 lr=1.00e-03
[Epoch 22/30] train_loss=64.6903 val_loss=116.6728 best_val=116.1028 lr=5.00e-04
[Epoch 23/30] train_loss=64.2932 val_loss=115.6295 best_val=115.6295 lr=5.00e-04
[Epoch 24/30] train_loss=63.3800 val_loss=115.7151 best_val=115.6295 lr=5.00e-04
[Epoch 25/30] train_loss=63.7474 val_loss=115.5679 best_val=115.5679 lr=5.00e-04
[Epoch 26/30] train_loss=63.0829 val_loss=116.5652 best_val=115.5679 lr=5.00e-04
[Epoch 27/30] train_loss=62.9968 val_loss=116.5559 best_val=115.5679 lr=5.00e-04
[Epoch 28/30] train_loss=63.4564 val_loss=115.7752 best_val=115.5679 lr=2.50e-04
[Epoch 29/30] train_loss=63.0947 val_loss=116.3796 best_val=115.5679 lr=2.50e-04
[Epoch 30/30] train_loss=62.5578 val_loss=115.8926 best_val=115.5679 lr=2.50e-04
Saved checkpoint: tdrive_predictor_artifacts\phase_b_sp\gru_phase_curv_step.pt
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> 
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-taxi> python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_b_sp --mode curv_step --graphml .\osm\beijing_taxid.graphml
>>
Metrics: {'ADE': 978.8319091796875, 'FDE': 1827.216552734375, 'Hit@100': 0.2931815981864929, 'Hit@200': 0.3398591876029968, 'Hit@400': 0.3639695346355438, 'PerHorizonError': {'h1': 384.5330810546875, 'h3': 679.6910400390625, 'h5': 1023.8865966796875, 'h10': 1827.216552734375}, 'PerHorizonHit@200': {'h1': 0.5282090847719163, 'h3': 0.4107435625421931, 'h5': 0.37342077345935, 'h10': 0.33985919567942907}}
(.venv) (base) PS C:\Users\Surface1\Documents\Serverless-edge-computing-simulation\predict-model-with-tax 





 python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --lookback 20 --epochs 80 --batch-size 256 --hidden-size 512 --target-scale 1.0 --early-stop-patience 6 --early-stop-min-delta 0.1 --device cuda --num-workers 16
                                                                                                                 [Epoch 1/80] train_loss=15.2992 val_loss=94.7642 best_val=94.7642 lr=1.00e-03                                        
[Epoch 2/80] train_loss=24.7745 val_loss=93.2517 best_val=93.2517 lr=1.00e-03                                        
[Epoch 3/80] train_loss=34.8725 val_loss=92.3581 best_val=92.3581 lr=1.00e-03                                        
[Epoch 4/80] train_loss=45.0557 val_loss=91.7738 best_val=91.7738 lr=1.00e-03                                        
[Epoch 5/80] train_loss=55.2087 val_loss=91.8344 best_val=91.7738 lr=1.00e-03                                        
[Epoch 6/80] train_loss=55.2345 val_loss=92.7590 best_val=91.7738 lr=1.00e-03                                        
[Epoch 7/80] train_loss=55.1191 val_loss=91.4695 best_val=91.4695 lr=1.00e-03                                        
[Epoch 8/80] train_loss=55.1275 val_loss=91.6237 best_val=91.4695 lr=1.00e-03                                        
[Epoch 9/80] train_loss=55.0239 val_loss=91.7865 best_val=91.4695 lr=1.00e-03                                        
[Epoch 10/80] train_loss=55.0588 val_loss=91.3739 best_val=91.4695 lr=1.00e-03                                       
[Epoch 11/80] train_loss=54.9233 val_loss=91.2300 best_val=91.2300 lr=1.00e-03                                       
[Epoch 12/80] train_loss=55.0283 val_loss=91.1347 best_val=91.2300 lr=1.00e-03                                       
[Epoch 13/80] train_loss=54.8924 val_loss=91.3860 best_val=91.2300 lr=1.00e-03                                       
[Epoch 14/80] train_loss=54.9122 val_loss=91.3593 best_val=91.2300 lr=1.00e-03                                       
[Epoch 15/80] train_loss=54.9123 val_loss=91.0357 best_val=91.0357 lr=1.00e-03                                       
[Epoch 16/80] train_loss=54.8186 val_loss=91.4407 best_val=91.0357 lr=1.00e-03                                       
[Epoch 17/80] train_loss=54.8242 val_loss=91.1976 best_val=91.0357 lr=1.00e-03                                       
[Epoch 18/80] train_loss=54.8162 val_loss=91.3877 best_val=91.0357 lr=5.00e-04                                       
[Epoch 19/80] train_loss=54.3635 val_loss=90.7461 best_val=90.7461 lr=5.00e-04                                       
[Epoch 20/80] train_loss=54.3398 val_loss=90.5823 best_val=90.5823 lr=5.00e-04                                       
[Epoch 21/80] train_loss=54.2366 val_loss=90.5993 best_val=90.5823 lr=5.00e-04                                       
[Epoch 22/80] train_loss=54.2966 val_loss=90.6142 best_val=90.5823 lr=5.00e-04                                       
[Epoch 23/80] train_loss=54.3520 val_loss=90.6904 best_val=90.5823 lr=2.50e-04                                       
[Epoch 24/80] train_loss=54.0613 val_loss=90.3837 best_val=90.3837 lr=2.50e-04                                       
[Epoch 25/80] train_loss=54.0165 val_loss=90.2525 best_val=90.2525 lr=2.50e-04                                       
[Epoch 26/80] train_loss=54.0092 val_loss=90.2190 best_val=90.2525 lr=2.50e-04                                       
[Epoch 27/80] train_loss=53.9797 val_loss=90.2356 best_val=90.2525 lr=2.50e-04                                       
[Epoch 28/80] train_loss=53.9791 val_loss=90.2923 best_val=90.2525 lr=2.50e-04                                       
[Epoch 29/80] train_loss=53.9527 val_loss=90.1597 best_val=90.2525 lr=2.50e-04                                       
[Epoch 30/80] train_loss=53.9270 val_loss=90.1519 best_val=90.1519 lr=2.50e-04                                       
[Epoch 31/80] train_loss=53.9554 val_loss=90.1435 best_val=90.1519 lr=2.50e-04                                       
[Epoch 32/80] train_loss=53.9323 val_loss=90.2107 best_val=90.1519 lr=2.50e-04                                       
[Epoch 33/80] train_loss=53.9196 val_loss=90.1094 best_val=90.1519 lr=2.50e-04                                       
[Epoch 34/80] train_loss=53.8850 val_loss=90.3561 best_val=90.1519 lr=2.50e-04                                       
[Epoch 35/80] train_loss=53.8694 val_loss=90.1179 best_val=90.1519 lr=2.50e-04                                       
[Epoch 36/80] train_loss=53.8680 val_loss=90.1692 best_val=90.1519 lr=1.25e-04           
(.venv) truongnx@jackson:~/toanlncode/Serverless-edge-computing-simulation/predict-model-with-taxi$ python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts/phase_b_5k_fast --mode curv_step --graphml ./osm/beijing_tax
id.graphml
/home/truongnx/toanlncode/Serverless-edge-computing-simulation/predict-model-with-taxi/tdrive_predictor/evaluate.py:53: FutureWarning: You are using `torch.load` with `weights_only=False` (the current default value), which uses the default pickle module implicitly. It is possible to construct malicious pickle data which will execute arbitrary code during unpickling (See https://github.com/pytorch/pytorch/blob/main/SECURITY.md#untrusted-models for more details). In a future release, the default value for `weights_only` will be flipped to `True`. This limits the functions that could be executed during unpickling. Arbitrary objects will no longer be allowed to be loaded via this mode unless they are explicitly allowlisted by the user via `torch.serialization.add_safe_globals`. We recommend you start setting `weights_only=True` for any use case where you don't have full control of the loaded file. Please open an issue on GitHub for any issues related to this experimental feature.
  ckpt = torch.load(ckpt_path, map_location=device)
Metrics: {'ADE': 704.5794067382812, 'FDE': 1326.8875732421875, 'Hit@100': 0.44184792041778564, 'Hit@200': 0.5092555284500122, 'Hit@400': 0.5633185505867004, 'PerHorizonError': {'h1': 244.22714233398438, 'h3': 496.4449462890625, 'h5': 750.757080078125, 'h10': 1326.8875732421875}, 'PerHorizonHit@200': {'h1': 0.6894228988389862, 'h3': 0.566739198938261, 'h5': 0.5362888112753595, 'h10': 0.5092555450321831}}


[Phase B] Segmented trips=221331 | max_idle_gap_min=15
[Phase B] Graph loaded | source=graphml | elapsed=4.9s
[Phase B] Graph-context features enabled | nodes=55328 | junction_nodes=48237
[Phase B] HMM params | sigma=12.0 | radius=150.0 | K=6 | beam=10 | turn_penalty=0.0 | sp=False | road_resample=True
[Phase B] Split sizes | train=17660259 val=2475145 test=1973089                                                                                                                             
[Phase B] Saved artifacts to tdrive_predictor_artifacts/phase_b_7k_fast | fallback_ratio=0.19781298763084515 | elapsed=10037.7s
(serverless-sim) truongnx@jackson:~/Serverless-edge-computing-simulation/predict-model-with-taxi$ python -m tdrive_predictor.cli prepare   --tdrive-root "./T-drive Taxi Trajectories/release/taxi_log_2008_by_id"   --num-taxis 7000   --max-idle-gap-min 15   --use-osm   --graphml ./osm/beijing_taxid.graphml   --cand-radius-m 150   --k-candidates 6   --beam-size 10   --sigma-gps-m 12   --road-resample   --out-dir tdrive_predictor_artifacts/phase_b_7k_fast^C
(serverless-sim) truongnx@jackson:~/Serverless-edge-computing-simulation/predict-model-with-taxi$ 

Metrics: {
  'ADE': 201.66151428222656,
  'FDE': 417.7447204589844,
  'Hit@100': 0.70894855260849,
  'Hit@200': 0.74758476018,
  'Hit@400': 0.7856186628341675,
  'PerHorizonError': {
    'h1': 27.6619930267334,
    'h3': 120.45806884765625,
    'h5': 240.7806396484375,
    'h10': 417.7447204589844
  },
  'PerHorizonHit@200': {
    'h1': 0.9621487944834411,
    'h3': 0.8175736028049158,
    'h5': 0.7031487938357145,
    'h10': 0.7475847890451278
  }
}


export TDRIVE_ARTIFACT_DIR="$HOME/Serverless-edge-computing-simulation/predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_7k_fast"
export TDRIVE_CKPT_NAME="gru_phase_curv_step.pt"
export TDRIVE_DEVICE="cuda"
