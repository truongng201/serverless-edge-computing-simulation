# Experiment Summary: `experiment_results_20251229_010356.csv`

- Users: `5000`
- Edge nodes: `300`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `2,751,912.9 ms (2,751.91 s)`
- median: `2,558,105.9 ms (2,558.11 s)`
- p95: `3,095,400.6 ms (3,095.40 s)`
- p99: `7,427,257.7 ms (7,427.26 s)`
- min/max: `752,257.1 ms (752.26 s)` / `7,427,257.9 ms (7,427.26 s)`

**Avg per user (ms/user)**
- mean: `550.383 ms`
- median: `511.621 ms`
- p95: `619.080 ms`
- p99: `1,485.5 ms (1.49 s)`
- min/max: `150.451 ms` / `1,485.5 ms (1.49 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `2,763,004.2 ms (2,763.00 s)`
- median: `2,506,880.9 ms (2,506.88 s)`
- p95: `3,850,650.8 ms (3,850.65 s)`
- p99: `7,427,257.7 ms (7,427.26 s)`
- min/max: `752,257.1 ms (752.26 s)` / `7,427,257.9 ms (7,427.26 s)`

**Avg per user (ms/user)**
- mean: `552.601 ms`
- median: `501.376 ms`
- p95: `770.130 ms`
- p99: `1,485.5 ms (1.49 s)`
- min/max: `150.451 ms` / `1,485.5 ms (1.49 s)`

