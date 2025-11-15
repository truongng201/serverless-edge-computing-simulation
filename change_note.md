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
