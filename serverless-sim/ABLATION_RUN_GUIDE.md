# Ablation Grid — Run Guide

Run the ablation grid (Table IV) + per-request latency (p95/p99/jitter/CDF)
on the server (where the predictor artifacts live). Noise sensitivity (§V.E) is a
separate follow-up batch.

## Simulation semantics (realism fixes, 2026-10)

**Results produced before these fixes are not comparable with new runs.** Re-run
every variant, including the baselines.

| Variant (algorithm string)                | Serves request at                  | Keep-alive  | Prewarm target (forecast)        |
|-------------------------------------------|------------------------------------|-------------|----------------------------------|
| `greedy`                                  | nearest feasible cloudlet          | OFF (TTL=0) | —                                |
| `greedy + keep-alive`                     | nearest feasible cloudlet          | ON          | —                                |
| `prediction without warm-state awareness` | cloudlet of forecast position      | ON          | —                                |
| `prewarm (persistence)`                   | nearest feasible cloudlet          | ON          | current position (≡ keep-alive)  |
| `prewarm (constant velocity)`             | nearest feasible cloudlet          | ON          | linear extrapolation, h=5 min    |
| `predictive`                              | nearest feasible cloudlet          | ON          | GRU predictor, h=5 min           |
| `prewarm (oracle)`                        | nearest feasible cloudlet          | ON          | true position at t+5 (upper bound) |

The prewarm variants share one mechanism and differ **only** in the forecast, so
`predictive` vs `prewarm (constant velocity)` / `prewarm (oracle)` measures the
value of the learned predictor. All of them start prewarming only once a user has
`TDRIVE_HISTORY_LENGTH` (20) observed points.

What a run now models (all in `config.py`, env-overridable):

- **One step = 60 s** of trajectory time (`SIM_STEP_DURATION_S`). Each active user
  issues one request every `REQUEST_INTERVAL_STEPS` (1) steps. Metrics count only
  the requests issued in that step (previously one execution every 5 steps was
  re-counted on each step until the next one).
- **Prewarm is real and billed.** A container launched at step *t* occupies a
  pool slot at once (may evict LRU) but serves requests only from
  *t* + `PREWARM_READY_DELAY_STEPS` (1). Every launch pays cold-start energy.
  Each launch ends up as exactly one `prewarm_hits` (served ≥ 1 request) or
  `prewarm_wasted` (expired/evicted unused, or a request arrived while it was
  still launching). The user is **not** forced onto the forecast cloudlet, so a
  wrong forecast wastes the launch and the request goes cold.
- **Keep-alive:** `WARM_TTL_STEPS` = 10 (10 min, OpenWhisk default). Retained
  containers cost `CONTAINER_IDLE_POWER_W` (0.075 W = 256 MB × 0.3 W/GB) for each
  step they are kept after their last use (`keepalive_energy_j`).
- **Energy** is integrated over 60 s per step, with fixed power profiles
  (`EDGE_*_W`, `CENTRAL_*_W`) instead of psutil detection on the host. Every
  request pays execution energy; a cold request also pays the init energy. DT
  migration energy is billed per real handoff, not per cold start.
  `variable_energy_j` = total − static is the policy-dependent part: report it
  alongside the total, since static power dominates the total.
- **Taxis leave when their trip ends** (`REPLAY_END_BEHAVIOR=depart`). Before,
  they parked at their last point and kept requesting; in the local pools that
  was 63–75% of all user-steps. The active population therefore shrinks over a
  run. Use the request-weighted metrics (`latency_per_request_ms`, `warm_rate`)
  and report `requests`. `REPLAY_MIN_TRIP_STEPS` filters short trips from the cohort.
- **Capacity:** every variant books every assigned user against
  `MAX_CONCURRENT_PER_EDGE` (the old predictive path skipped users that did not
  switch). Overflow goes to the central cloud, which pays `CENTRAL_WAN_EXTRA_MS`
  (20 ms) extra one-way latency.
- **Handoff migration** moves DT state over the wired backhaul
  (`BACKHAUL_BANDWIDTH_BYTES_PER_MS` = 1 Gbps, ≈4 ms for 512 KB), charged to the
  user's next request. Previously it used the user's 4G link (≈175 ms).
- **No silent fallback:** `predictive` and `prediction without warm-state
  awareness` raise `PredictorUnavailableError` if the predictor is not loaded
  (`STRICT_PREDICTIVE=1`). Before, they quietly ran greedy under a predictive label.

New CSV columns: `requests, handoffs, prewarm_launches, prewarm_hits,
prewarm_wasted, live_containers, execution_energy_j, keepalive_energy_j,
prewarm_energy_j, variable_energy_j`.

Tests: `python -m pytest tests -q` (no server, no predictor needed).

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

# 2. Run the grid (matrix is set in run_experiments.py main():
#    6 variants x USER_RANGES x EDGE_RANGES x 5 seeds [11,23,42,71,97], 300 steps)
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

The analyzer reports the minimum number of seeds per config so you can confirm
all 5 landed. `--warmup-steps N` drops the first N steps of every run (the
cold-system transient that is identical for all variants). It also still skips
rows with `unknown_count > 0` from old CSVs.

## Re-verify on the server (recommended)

```bash
# greedy vs keep-alive, same steps (no predictor needed)
python diag_keepalive.py
# full 4-variant distinctness + determinism + seed variance (needs predictor)
python smoke_test_ablation.py
```

## Notes / caveats for the paper

- `WARM_TTL_STEPS=10` (10 min). Sweep it (e.g. 5/10/30) for a sensitivity
  table: longer TTL trades keep-alive energy for fewer cold starts.
- `FUNCTION_NAME_BUCKETS=32`, `MAX_WARM_PER_NODE=16`: many users share a small
  function catalogue so reuse is meaningful; per-node pool caps at 16 (LRU evict).
- The 4.46% figure in the old draft is **not reproducible** from prior data;
  recompute the predictive-vs-baseline improvement from this grid and cite the
  exact (baseline, metric, config).
- Old `experiment_results_2026052*.csv` are single-seed and were produced with the
  buggy (duplicate) variants — do not reuse for Table IV.
