# Experiment Summary: `experiment_results_20251230_013903.csv`

- Users: `1000`
- Edge nodes: `100`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `556,902.2 ms (556.90 s)`
- median: `519,375.0 ms (519.38 s)`
- p95: `631,980.1 ms (631.98 s)`
- p99: `1,481,850.3 ms (1,481.85 s)`
- min/max: `150,450.3 ms (150.45 s)` / `1,481,850.3 ms (1,481.85 s)`

**Avg per user (ms/user)**
- mean: `556.902 ms`
- median: `519.375 ms`
- p95: `631.980 ms`
- p99: `1,481.9 ms (1.48 s)`
- min/max: `150.450 ms` / `1,481.9 ms (1.48 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `552,517.6 ms (552.52 s)`
- median: `503,476.9 ms (503.48 s)`
- p95: `955,916.0 ms (955.92 s)`
- p99: `1,482,454.0 ms (1,482.45 s)`
- min/max: `150,450.4 ms (150.45 s)` / `1,482,454.8 ms (1,482.45 s)`

**Avg per user (ms/user)**
- mean: `552.518 ms`
- median: `503.477 ms`
- p95: `955.916 ms`
- p99: `1,482.5 ms (1.48 s)`
- min/max: `150.450 ms` / `1,482.5 ms (1.48 s)`

## Comparison (predictive vs greedy)
- Mean total TAT delta: `-0.79%` (predictive vs greedy)
- Mean cold-start time delta: `-4.17%` (predictive vs greedy)
- Mean cold-start count delta: `-5.22%` (predictive vs greedy)

