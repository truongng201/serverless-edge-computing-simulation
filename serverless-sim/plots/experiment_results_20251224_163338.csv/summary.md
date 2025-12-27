# Experiment Summary: `experiment_results_20251224_163338.csv`

- Users: `1000`
- Edge nodes: `100`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `552,619.0 ms (552.62 s)`
- median: `511,052.0 ms (511.05 s)`
- p95: `614,245.6 ms (614.25 s)`
- p99: `1,489,053.0 ms (1,489.05 s)`
- min/max: `150,452.9 ms (150.45 s)` / `1,489,053.0 ms (1,489.05 s)`

**Avg per user (ms/user)**
- mean: `552.619 ms`
- median: `511.052 ms`
- p95: `614.246 ms`
- p99: `1,489.1 ms (1.49 s)`
- min/max: `150.453 ms` / `1,489.1 ms (1.49 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `553,296.2 ms (553.30 s)`
- median: `500,852.0 ms (500.85 s)`
- p95: `741,782.8 ms (741.78 s)`
- p99: `1,489,053.0 ms (1,489.05 s)`
- min/max: `150,452.9 ms (150.45 s)` / `1,489,053.0 ms (1,489.05 s)`

**Avg per user (ms/user)**
- mean: `553.296 ms`
- median: `500.852 ms`
- p95: `741.783 ms`
- p99: `1,489.1 ms (1.49 s)`
- min/max: `150.453 ms` / `1,489.1 ms (1.49 s)`

