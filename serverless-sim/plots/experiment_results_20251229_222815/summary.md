# Experiment Summary: `experiment_results_20251229_222815.csv`

- Users: `1000`
- Edge nodes: `50`

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
- mean: `560,367.8 ms (560.37 s)`
- median: `507,150.0 ms (507.15 s)`
- p95: `822,218.3 ms (822.22 s)`
- p99: `1,481,850.3 ms (1,481.85 s)`
- min/max: `150,450.3 ms (150.45 s)` / `1,481,850.3 ms (1,481.85 s)`

**Avg per user (ms/user)**
- mean: `560.368 ms`
- median: `507.150 ms`
- p95: `822.218 ms`
- p99: `1,481.9 ms (1.48 s)`
- min/max: `150.450 ms` / `1,481.9 ms (1.48 s)`

## Comparison (predictive vs greedy)
- Mean total TAT delta: `+0.62%` (predictive vs greedy)
- Mean cold-start time delta: `+2.51%` (predictive vs greedy)
- Mean cold-start count delta: `+1.58%` (predictive vs greedy)

