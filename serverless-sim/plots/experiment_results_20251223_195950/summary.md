# Experiment Summary: `experiment_results_20251223_195950.csv`

- Users: `300`
- Edge nodes: `20`

## Metrics
- `total_turnaround_time` is the SUM across all current users (ms).
- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).

### `greedy`

**Total TAT (sum over users)**
- mean: `686,681.8 ms (686.68 s)`
- median: `705,212.2 ms (705.21 s)`
- p95: `729,734.9 ms (729.73 s)`
- p99: `729,961.1 ms (729.96 s)`
- min/max: `45,135.7 ms (45.14 s)` / `729,961.1 ms (729.96 s)`

**Avg per user (ms/user)**
- mean: `2,288.9 ms (2.29 s)`
- median: `2,350.7 ms (2.35 s)`
- p95: `2,432.4 ms (2.43 s)`
- p99: `2,433.2 ms (2.43 s)`
- min/max: `150.452 ms` / `2,433.2 ms (2.43 s)`

### `predictive`

**Total TAT (sum over users)**
- mean: `694,300.8 ms (694.30 s)`
- median: `728,425.6 ms (728.43 s)`
- p95: `732,663.9 ms (732.66 s)`
- p99: `733,044.9 ms (733.04 s)`
- min/max: `45,135.7 ms (45.14 s)` / `733,045.0 ms (733.04 s)`

**Avg per user (ms/user)**
- mean: `2,314.3 ms (2.31 s)`
- median: `2,428.1 ms (2.43 s)`
- p95: `2,442.2 ms (2.44 s)`
- p99: `2,443.5 ms (2.44 s)`
- min/max: `150.452 ms` / `2,443.5 ms (2.44 s)`

