# Workspace Summary — predict-model-with-taxi

This document summarizes what exists in this folder, current progress, how to run the code, and what remains according to `T-drive Taxi Trajectories/Implementation-docs.md`.

## Contents Overview

- Raw dataset (T-Drive)
  - `T-drive Taxi Trajectories/release/taxi_log_2008_by_id/` — original logs (`taxi_id, timestamp, lon, lat`).
  - `T-drive Taxi Trajectories/Implementation-docs.md` — Stage 1 spec (data → HMM → resample → features → baselines → GRU → metrics).
  - `T-drive Taxi Trajectories/release/user_guide.pdf` — dataset description.

- Model/pipeline package: `tdrive_predictor/`
  - Core
    - `prepare.py` — Phase A/B data preparation (free‑space and OSM/HMM branches).
    - `cli.py` — CLI entry with subcommands: `prepare`, `train`, `eval`, `eval-ctrv`, `eval-markov`.
    - `dataset.py` — sequence windowing for horizons {1,3,5,10}.
    - `model.py` — GRU head predicting Δx,Δy for 4 horizons.
    - `train.py`, `evaluate.py`, `metrics.py`, `utils.py`.
  - Baselines
    - `baselines/ctrv.py` — CTRV (EKF) baseline; optional snap-to-road in Phase B.
    - `baselines/markov.py` — hour-conditioned segment Markov baseline (no semantics).
  - OSM/Map-matching
    - `osm/loader.py` — load/cached GraphML, or build from local OSM XML (`--xml`), or download via Overpass (`--place/--bbox`, mirrors/timeouts supported).
    - `mapmatch/hmm.py` — CandidateGenerator (STRtree), emission=Gaussian(distance), transition (length vs Δt/vmax), Viterbi + fallback.
    - `resample/road_resample.py` — initial road-based resampling (optional `--road-resample`).
    - `features/semantics.py` — stub; not used per current scope.

- Docs & reports
  - `QUICKSTART-PhaseA.md` — setup, run Phase A.
  - `QUICKSTART-PhaseB.md` — setup, run Phase B (incl. offline XML flow).
  - `Progress-Report.md` — what works, sample results, fixes, next steps.
  - `WORKSPACE-SUMMARY.md` (this file) — inventory + status + remaining work.

- Artifacts (git-ignored)
  - `tdrive_predictor_artifacts/phase_a` (or `_200`, `_500`, etc.) — train/val/test pickles, scaler, meta, GRU ckpt.
  - `tdrive_predictor_artifacts/phase_b` — Phase B equivalents.
  - `osm/*.graphml`, `osm/*.osm` — cached graphs / local OSM.

## Current Progress

- Phase A (Free‑Space) — Completed
  - Load → WGS84→UTM 50N → segment trips (`--max-idle-gap-min`) → speed outlier filter → per‑minute resample (union index, time interpolation) → features (v, a, Δv, Δheading, stop/dwell, ToD/DoW/rush hour) → day split (2–6 train, 7 val, 8 test) → z-score normalization.
  - GRU Δx,Δy model + CLI train/eval.
  - Baseline CTRV (EKF) runs on Phase A.
  - Sample metrics (50 taxis): GRU ADE≈768.7 m, FDE≈1526.9 m, Hit@100/200/400≈0.512/0.518/0.530. CTRV gives ADE≈728 m, FDE≈1651 m on same data.

- Phase B (OSM + HMM) — Implemented (core) and integrated
  - OSM loader: cached GraphML; offline `--xml` support to avoid Overpass; mirror/timeout flags.
  - HMM: candidates via STRtree; emission Gaussian; transition by path length vs Δt/vmax (Euclid by default, optional shortest‑path); Viterbi with fallback.
  - Prepare Phase B: map‑match → build footpoints → per‑minute resample (time‑based) → features/splits.
  - Optional `--road-resample` (initial) to resample along road segments.
  - Baselines: Markov on segments (Phase B recommended), CTRV snap (snap horizons to nearest road).

## How To Run (Quick)

From `predict-model-with-taxi` in your venv.

- Phase A
  - Prepare: `python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts\phase_a`
  - Train:   `python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_a --epochs 10 --lookback 20`
  - Eval:    `python -m tdrive_predictor.cli eval  --data-dir tdrive_predictor_artifacts\phase_a`
  - Baseline CTRV: `python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_a --lookback 20`

- Phase B (recommended offline XML or pre-cached GraphML)
  - Offline XML (example): `--xml predict-model-with-taxi\osm\beijing_paper.osm`
  - Or cached graph: `--graphml predict-model-with-taxi\osm\beijing_paper.graphml`
  - Prepare: `python -m tdrive_predictor.cli prepare --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" --num-taxis 30 --max-idle-gap-min 15 --use-osm --graphml predict-model-with-taxi\osm\beijing_paper.graphml --out-dir tdrive_predictor_artifacts\phase_b --cand-radius-m 50 --k-candidates 5 --sigma-gps-m 12`
  - Train/Eval: same as Phase A but use `--data-dir tdrive_predictor_artifacts\phase_b`
  - Markov baseline: `python -m tdrive_predictor.cli eval-markov --data-dir tdrive_predictor_artifacts\phase_b --graphml predict-model-with-taxi\osm\beijing_paper.graphml --lookback 20`
  - CTRV snap: `python -m tdrive_predictor.cli eval-ctrv --data-dir tdrive_predictor_artifacts\phase_b --lookback 20 --snap --graphml predict-model-with-taxi\osm\beijing_paper.graphml`

## Remaining Work (per Implementation‑docs)

- Map‑Matching & Resampling
  - [x] HMM (candidates + emission + transition + Viterbi) and integration in prepare.
  - [~] Road‑based per‑minute resampling along polylines (curvilinear) — initial option `--road-resample` exists; refine path stitching across edges.

- Baselines
  - [x] CTRV (EKF) baseline; add robust “snap‑to‑road” per step (current: snap horizons).
  - [x] Markov on segments (hour‑conditioned transitions with Laplace smoothing).

- Main Model (Stage 1)
  - [x] GRU Δx,Δy (free‑space) trained/evaluated on Phase A.
  - [ ] Road‑aware GRU: snap after each predicted step; optional curvilinear displacement head; scheduled sampling schedule.

- Evaluation & Ablations
  - [x] ADE/FDE/Hit@R final step.
  - [ ] Per‑horizon metrics (1/3/5/10) table.
  - [ ] Slices: by original sampling gap, time‑of‑day, inner vs outer area.
  - [ ] Ablations: without map‑matching; without temporal features; without scheduled sampling.

- Artifacts & Logging
  - [x] Export predictions & scaler; record meta (HMM params, graph source, resample mode).
  - [ ] Add a concise model card and per‑run config/log summary.

- Risks & Mitigations (tracking)
  - Overpass timeouts → use offline XML / cached GraphML / bbox.
  - OSM vs 2008 mismatch → allow fallback free‑space; monitor fallback ratio.
  - HMM runtime → prune K=3–5, radius 30–50 m, small bbox, optional shortest‑path.

## Suggestions / Clean‑ups

- CLI & Meta
  - Prefer explicit graph source order: `graphml > xml > place/bbox`; warn if multiple provided.
  - Log chosen HMM params (`cand_radius_m`, `k_candidates`, `sigma_gps_m`, `use_shortest_path`, `use_road_resample`) in console and meta.

- HMM
  - Keep robust dt computation via pandas Timedelta.
  - Consider caching nearest edge IDs during prepare for faster Markov baseline.

- Resampling
  - Improve `resample_on_road` to stitch across edges by cumulative s and segment traversal rather than time‑only interpolation between footpoints.

- Baselines
  - CTRV snap: prefer topologically contiguous edge to reduce jumps.

- Reporting
  - Add per‑horizon ADE/FDE/Hit@R; add slice plots; update `Progress-Report.md` with Phase B results.

---
If you want, I can run a small Phase B job using your local OSM XML (`--xml`) and provide a side‑by‑side comparison vs Phase A here.
