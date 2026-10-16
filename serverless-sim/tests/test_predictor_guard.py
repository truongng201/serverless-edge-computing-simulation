"""A predictive run must never silently degrade into greedy.

If the T-Drive predictor cannot be loaded (missing artifact directory, missing
torch, bad checkpoint) the scheduler used to log a warning and fall back to
greedy placement. The run was still recorded in the results CSV as
`predictive`, producing data that is indistinguishable from a real predictive
run but is actually the greedy baseline.
"""
import pytest

from central_node.control_layer.scheduler_module.scheduler import (
    AssignmentAlgorithm,
    PredictorUnavailableError,
    Scheduler,
)


def test_predictor_ready_is_false_when_adapter_missing(scheduler):
    scheduler.predictor_adapter = None

    assert scheduler.predictor_ready is False


def test_predictive_raises_instead_of_falling_back_to_greedy(populated_scheduler):
    populated_scheduler.predictor_adapter = None
    populated_scheduler.set_assignment_algorithm(AssignmentAlgorithm.PREDICTIVE.value)

    with pytest.raises(PredictorUnavailableError):
        populated_scheduler.node_assignment()


def test_prediction_without_warm_state_also_raises(populated_scheduler):
    populated_scheduler.predictor_adapter = None
    populated_scheduler.set_assignment_algorithm(AssignmentAlgorithm.PREDICTIVE_NO_WARM.value)

    with pytest.raises(PredictorUnavailableError):
        populated_scheduler.node_assignment()


def test_greedy_is_unaffected_by_missing_predictor(populated_scheduler):
    populated_scheduler.predictor_adapter = None
    populated_scheduler.set_assignment_algorithm(AssignmentAlgorithm.GREEDY.value)

    matrix = populated_scheduler.node_assignment()

    assert len(matrix) == len(populated_scheduler.user_nodes)


def test_legacy_fallback_still_available_when_strict_mode_disabled(populated_scheduler, monkeypatch):
    """Opt-out escape hatch for demos, off by default."""
    from config import Config

    monkeypatch.setattr(Config, "STRICT_PREDICTIVE", False)
    populated_scheduler.predictor_adapter = None
    populated_scheduler.set_assignment_algorithm(AssignmentAlgorithm.PREDICTIVE.value)

    matrix = populated_scheduler.node_assignment()

    assert len(matrix) == len(populated_scheduler.user_nodes)


def test_predictor_ready_surfaces_in_cluster_status(scheduler):
    scheduler.predictor_adapter = None

    status = scheduler.get_cluster_status()

    assert status["predictor_ready"] is False
