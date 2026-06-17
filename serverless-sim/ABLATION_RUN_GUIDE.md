# Ablation Grid — Run Guide

Run the 80-run ablation grid (Table IV) + per-request latency (p95/p99/jitter/CDF)
on the server (where the predictor artifacts live). Noise sensitivity (§V.E) is a
separate follow-up batch.

## What changed (Phase 0 + 1 + 2)

The 4 variants are now **correctly distinct** (previously 2 pairs were byte-identical):

| Variant (algorithm string)                     | Placement   | Keep-alive | Prewarm |
|------------------------------------------------|-------------|------------|---------|
| `greedy`                                       | greedy      | OFF (TTL=0)| no      |
| `greedy + keep-alive`                          | greedy      | ON         | no      |
| `prediction without warm-state awareness`      | predictive  | ON         | no      |
| `predictive`                                   | predictive  | ON         | YES     |

- Warm/cold is now decided by the **warm pool** (`lookup`/`admit_cold`), keyed by
  `(node, function)`, on the **simulation-step clock**. TTL = `WARM_TTL_STEPS` (30)
  for every variant except plain `greedy` (TTL=0 = no cross-step reuse baseline).
- Prewarm is bound to the `predictive` variant (no longer a hardcoded global).
- `seed` is plumbed through `/set_dataset`; it drives a **reproducible random
  cohort** of taxis (so 5 seeds give genuine variance for CI).
- Per-request latency logged to `PER_REQUEST_LOG_DIR` (one gzip CSV per run).

Verified locally (greedy-family, no predictor): keep-alive raises warm reuse,
same seed reproduces exactly, different seeds differ. **Predictive variants must be
verified on the server** (predictor artifacts not present locally).

## Prerequisite — replay pool ≥ 5000 trajectories

`taxiD_Replay` samples users from a pickled pool. A run requesting more users than
the pool holds silently runs with `pool_size` users (the runner now logs a WARNING).
For a true 5000-user run, regenerate the pool from the held-out test split first:

```bash
# from serverless-sim/, on the server (artifacts present)
python scripts/export_taxid_replay_last1k.py \
    --phaseb-dir ../predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_7k_fast \
    --num-trips 5000 --include-features
# -> writes mock_data/taxid_replay_5000_features.pkl (loader picks this up first)
```

If the test split has < 5000 trips, use `--num-trips all` and drop the 5000-user
column (or point `--phaseb-dir` at a larger artifact set).

## Run the grid

```bash
# 1. Start the central node WITH per-request logging
cd serverless-sim
PER_REQUEST_LOG_DIR=request_logs python central_main.py --port 8000 --log-level WARNING &

# 2. Run the 80-run grid (matrix is set in run_experiments.py main():
#    4 variants x {100,500,1000,5000} users x 5 seeds [11,23,42,71,97] @ 10 edges, 300 steps)
python run_experiments.py
#    -> streams experiment_results_<ts>.csv  (one row per timestep, includes `seed`)
#    -> request_logs/req_<algo>_u<users>_e<edges>_s<seed>_<ts>.csv.gz per run
```

Override the matrix without editing the file via env is not wired; edit the
`USER_RANGES / EDGE_RANGES / ALGORITHMS / SEEDS / DURATION_S` block in
`run_experiments.py main()` if you want a different grid.

> Runtime: the 5000-user runs dominate. Do a single 5000-user timing run first to
> estimate total wall-clock before launching all 80.

## Analyze → Table IV + CDF

```bash
# Table IV: mean +/- 95% CI over seeds (Student-t, t=2.776 for n=5)
python analyze_ablation.py experiment_results_<ts>.csv --latex
#   -> prints Table IV per metric + LaTeX rows
#   -> writes table_iv.csv

# Per-request: p95/p99/jitter per run + pooled CDF for plotting
python analyze_ablation.py experiment_results_<ts>.csv \
    --requests request_logs --cdf-out cdf_data.csv
```

The analyzer skips warm-up rows (steps before the first execution, where
`unknown_count > 0`) and reports the minimum number of seeds per config so you can
confirm all 5 landed.

## Re-verify on the server (recommended)

```bash
# greedy vs keep-alive, same steps (no predictor needed)
python diag_keepalive.py
# full 4-variant distinctness + determinism + seed variance (needs predictor)
python smoke_test_ablation.py
```

## Notes / caveats for the paper

- `WARM_TTL_STEPS=30` makes keep-alive very generous (≈0 cold after warm-up). Tune
  via env `WARM_TTL_STEPS` if you want a tighter keep-alive window.
- `FUNCTION_NAME_BUCKETS=32`, `MAX_WARM_PER_NODE=16`: many users share a small
  function catalogue so reuse is meaningful; per-node pool caps at 16 (LRU evict).
- The 4.46% figure in the old draft is **not reproducible** from prior data;
  recompute the predictive-vs-baseline improvement from this grid and cite the
  exact (baseline, metric, config).
- Old `experiment_results_2026052*.csv` are single-seed and were produced with the
  buggy (duplicate) variants — do not reuse for Table IV.
