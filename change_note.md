[2025-11-15] Added tdrive_predictor inference service and serverless bridge (tdrive_inference) for mobility prediction.
[2025-11-15] Added export_taxid_replay_last1k.py to generate replay trajectories (last N Phase B trips) for TaxiD simulation.
[2025-11-15] Integrated predictive scheduler scaffolding: user history tracking, T-Drive adapter hook, config knobs.

python serverless-sim/scripts/export_taxid_replay_last1k.py `
  --phaseb-dir predict-model-with-taxi/tdrive_predictor_artifacts/phase_b_5k_fast `
  --out-path serverless-sim/mock_data/taxid_replay_last1k.pkl `
  --num-trips 1000

[2025-11-16] Fixed Config predictive block syntax and wired StartTaxiDReplaySampleController into controller __init__, central_core, and central_route.
[2025-11-16] Implemented taxid_replay dataset playback in GetAllUsersController and ensured scheduler.update_user_node appends history for predictive inference.
[2025-11-16] Updated T-Drive inference bridge to add predict-model-with-taxi to sys.path so tdrive_predictor can be imported from serverless-sim.
[2025-11-16] Updated simulation-ui DatasetSelectionCard and start-sample helpers to add a new 'TaxiD Replay (last 1000 trips)' dataset that calls /start_taxid_replay_sample and reuses TaxiD road overlays.
[2025-11-16] Tweaked SimulationCanvas user connection drawing to use thinner lines and smaller markers for central/edge assignments.
[2025-11-16] Changed central/edge execute_function to use a stable per-user function_name (fn_<user_id>), reuse warm containers only for matching function_name, and increased DEFAULT_MAX_WARM_TIME to 60s so cold starts mainly occur on node migrations.
[2025-11-16] Fixed central_node execute_function active_requests accounting (increment on start, decrement in finally) so Active Requests reflects in-flight calls instead of accumulating.
[2025-11-16] Added Scheduler latency aggregation (record_tat_snapshot/calculate_total_turnaround_time/reset_metrics) and wired it into GetAllUsersController + ResetSimulationController so /performance_metrics returns average TAT over a test run.
[2025-11-16] Added SIMULATE_NODE_METRICS mode: edge/central now report synthetic CPU/memory usage based on container counts and active requests instead of host psutil metrics, making node health/resource constraints independent of the developer machine load.
[2025-11-16] Added SpreadEdgeNodesController + /edge_nodes/spread endpoint and a 'Spread Edge Nodes' button in SimulationControlsCard to arrange all edge nodes evenly around the central node from the UI.
[2025-11-16] Added tdrive_predictor/README-dev.md documenting prepare/train/eval pipeline, model modes, and file-by-file map of the predictor package.
[2025-11-24] Added progress logging for CTRV and Markov baselines in tdrive_predictor (CLI and baselines/markov.py) so long-running evals on Phase B 5k data print their status and window counts.
