# Experiment Summary: `experiment_results_20260117_000714.csv`

- Users: `2000`
- Edge nodes: `100`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `1,238,485.2 ms (1,238.49 s)`
- median: `1,171,358.6 ms (1,171.36 s)`
- p95: `1,534,021.6 ms (1,534.02 s)`
- p99: `2,991,083.9 ms (2,991.08 s)`
- min/max: `300,833.5 ms (300.83 s)` / `2,991,084.0 ms (2,991.08 s)`

**Avg per user (ms/user)**
- mean: `619.243 ms`
- median: `585.679 ms`
- p95: `767.011 ms`
- p99: `1,495.5 ms (1.50 s)`
- min/max: `150.417 ms` / `1,495.5 ms (1.50 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `981,344.3 ms (981.34 s)`
- median: `900,843.9 ms (900.84 s)`
- p95: `1,005,373.6 ms (1,005.37 s)`
- p99: `2,990,799.1 ms (2,990.80 s)`
- min/max: `300,833.7 ms (300.83 s)` / `2,990,802.2 ms (2,990.80 s)`

**Avg per user (ms/user)**
- mean: `490.672 ms`
- median: `450.422 ms`
- p95: `502.687 ms`
- p99: `1,495.4 ms (1.50 s)`
- min/max: `150.417 ms` / `1,495.4 ms (1.50 s)`

## Comparison (predictive vs greedy)
- Mean total TAT delta: `-20.76%` (predictive vs greedy)
- Mean cold-start time delta: `-71.11%` (predictive vs greedy)
- Mean cold-start count delta: `-71.12%` (predictive vs greedy)

