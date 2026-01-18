# Experiment Summary: `experiment_results_20251229_023252.csv`

- Users: `5000`
- Edge nodes: `500`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `2,752,279.9 ms (2,752.28 s)`
- median: `2,558,630.4 ms (2,558.63 s)`
- p95: `3,098,392.5 ms (3,098.39 s)`
- p99: `7,427,257.2 ms (7,427.26 s)`
- min/max: `752,256.5 ms (752.26 s)` / `7,427,257.3 ms (7,427.26 s)`

**Avg per user (ms/user)**
- mean: `550.456 ms`
- median: `511.726 ms`
- p95: `619.679 ms`
- p99: `1,485.5 ms (1.49 s)`
- min/max: `150.451 ms` / `1,485.5 ms (1.49 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `2,763,371.2 ms (2,763.37 s)`
- median: `2,507,405.4 ms (2,507.41 s)`
- p95: `3,851,647.6 ms (3,851.65 s)`
- p99: `7,427,257.2 ms (7,427.26 s)`
- min/max: `752,256.5 ms (752.26 s)` / `7,427,257.3 ms (7,427.26 s)`

**Avg per user (ms/user)**
- mean: `552.674 ms`
- median: `501.481 ms`
- p95: `770.330 ms`
- p99: `1,485.5 ms (1.49 s)`
- min/max: `150.451 ms` / `1,485.5 ms (1.49 s)`

