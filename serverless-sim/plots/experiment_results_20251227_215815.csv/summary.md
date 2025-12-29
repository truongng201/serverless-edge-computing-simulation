# Experiment Summary: `experiment_results_20251227_215815.csv`

- Users: `5000`
- Edge nodes: `50`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `2,436,492.5 ms (2,436.49 s)`
- median: `2,268,911.2 ms (2,268.91 s)`
- p95: `2,517,858.6 ms (2,517.86 s)`
- p99: `6,788,870.0 ms (6,788.87 s)`
- min/max: `752,571.0 ms (752.57 s)` / `6,788,870.7 ms (6,788.87 s)`

**Avg per user (ms/user)**
- mean: `487.298 ms`
- median: `453.782 ms`
- p95: `503.572 ms`
- p99: `1,357.8 ms (1.36 s)`
- min/max: `150.514 ms` / `1,357.8 ms (1.36 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `2,686,524.5 ms (2,686.52 s)`
- median: `2,253,546.2 ms (2,253.55 s)`
- p95: `6,824,604.6 ms (6,824.60 s)`
- p99: `7,503,550.6 ms (7,503.55 s)`
- min/max: `752,571.0 ms (752.57 s)` / `7,503,550.8 ms (7,503.55 s)`

**Avg per user (ms/user)**
- mean: `537.305 ms`
- median: `450.709 ms`
- p95: `1,364.9 ms (1.36 s)`
- p99: `1,500.7 ms (1.50 s)`
- min/max: `150.514 ms` / `1,500.7 ms (1.50 s)`

