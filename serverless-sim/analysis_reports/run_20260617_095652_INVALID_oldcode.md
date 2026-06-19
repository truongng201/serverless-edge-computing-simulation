# Ablation run report — experiment_results_20260617_095652.csv

- Analyzed: 2026-06-17
- Grid (structurally complete): 4 variants × {100,500,1000,5000} users × 5 seeds [11,23,42,71,97] @ 10 cloudlets = **80 runs**, 300 steps each, 24000 rows.
- Result: **unusable** — equivalent to the old buggy data (warm_rate ~0.95 for all variants, variants (c)≡(d), zero seed variance).

## Why it is invalid — diagnostic signatures (4/4 = OLD code)

| # | Signature | Observed | Meaning |
|---|-----------|----------|---------|
| 1 | seed 11 == 23 == 42 == 71 == 97 for every config | **identical** | seed had NO effect → old `set_dataset_controller` leading-slice cohort (`trajectories[:N]`) |
| 2 | `prediction without warm-state awareness` == `predictive` | **identical at all scales** | old string-mismatch + hardcoded prewarm → variants (c)/(d) not distinct |
| 3 | greedy warm_rate over first execution steps | **0.0 → rising to ~0.95** | old per-user warmth (`last_executed_node_id`), not new pool TTL=0 (~0.3 from step 1) |
| 4 | warm-up rows: `warm_count` vs `unknown_count` | **100 == 100 (clobber)** | old `get_performance_metrics` energy-clobber bug (warm_count = warm+unknown) |

Consequence: **all 95% CIs are ±0** (no cohort variance because the seed is ignored).

## Table IV (OLD-CODE NUMBERS — for the record only; mean ± 95% CI, all CI ≈ 0)

### Turnaround time (ms, step mean)
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 46 320 | 235 400 | 459 000 | 2 207 000 |
| greedy + keep-alive | 46 390 | 232 700 | 461 100 | 2 214 000 |
| prediction (no warm-state) | 44 220 | 224 200 | 453 300 | 2 198 000 |
| predictive | 44 220 | 224 200 | 453 300 | 2 198 000 |

### Cold starts (total over run)
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 1 200 | 6 900 | 10 500 | 30 500 |
| greedy + keep-alive | 1 275 | 6 613 | 11 940 | 33 270 |
| prediction (no warm-state) | 500 | 2 500 | 5 000 | 25 000 |
| predictive | 500 | 2 500 | 5 000 | 25 000 |

### Energy (J, total)
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 79 460 | 358 200 | 684 300 | 3 238 000 |
| greedy + keep-alive | 79 940 | 356 400 | 693 400 | 3 256 000 |
| prediction (no warm-state) | 75 040 | 330 400 | 649 600 | 3 203 000 |
| predictive | 75 040 | 330 400 | 649 600 | 3 203 000 |

### Warm rate
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 0.9595 | 0.9534 | 0.9645 | 0.9794 |
| greedy + keep-alive | 0.9569 | 0.9553 | 0.9597 | 0.9775 |
| prediction (no warm-state) | 0.9831 | 0.9831 | 0.9831 | 0.9831 |
| predictive | 0.9831 | 0.9831 | 0.9831 | 0.9831 |

### p95 latency (ms)
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 583.3 | 677.3 | 522.3 | 444.3 |
| greedy + keep-alive | 577.7 | 635.4 | 592.6 | 443.3 |
| prediction (no warm-state) | 466.5 | 534.1 | 535.4 | 448.4 |
| predictive | 466.5 | 534.1 | 535.4 | 448.4 |

### p99 latency (ms)
| variant | 100 | 500 | 1000 | 5000 |
|---|---|---|---|---|
| greedy | 909.3 | 1 200 | 1 090 | 522.4 |
| greedy + keep-alive | 979.8 | 1 080 | 1 051 | 641 |
| prediction (no warm-state) | 504.4 | 536.6 | 538.5 | 534.8 |
| predictive | 504.4 | 536.6 | 538.5 | 534.8 |

## Tell-tale anomalies (sanity red flags in the numbers themselves)
- Keep-alive has **more** cold starts than plain greedy (e.g. 1000u: 11 940 vs 10 500) — backwards; the warm-pool keep-alive is not wired in this run.
- (c) and (d) are byte-identical across all 7 metrics × 4 scales — they are the same run.
- All CI = 0 — impossible for a genuine 5-seed sample; confirms the seed is inert.

Expected after fix: distinct (c)≠(d), keep-alive < greedy in cold starts, warm_rate far below 0.95 for plain greedy, and non-zero CIs at 100/500/1000 users.
