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
[2025-11-24] Added progress logging for CTRV and Markov baselines in tdrive_predictor (CLI and baselines/markov.py) so long-running evals on Phase B 5k data print their status and window counts.
[2025-11-24] Extended tdrive_predictor curv_step training to support optional weighted step loss and higher scheduled sampling caps via env flags (TDRIVE_CURVSTEP_WEIGHTED_LOSS, TDRIVE_CURVSTEP_HIGH_SS); added optional graph-context features (node_degree, is_junction) in prepare_phase_b gated by TDRIVE_USE_GRAPH_CONTEXT_FEATURES.
[2025-11-24] Introduced road_rollout.rollout_curv_step_on_graph helper and refactored evaluate._evaluate_curv_step plus inference_service.predict_future_positions to use graph-constrained rollout when a Phase B road graph is provided (TDRIVE_GRAPHML_PATH), falling back to heading-based free-space rollout otherwise.
