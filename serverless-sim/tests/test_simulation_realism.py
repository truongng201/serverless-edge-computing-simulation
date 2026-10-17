"""Simulation semantics that the reported results depend on.

Each test pins down one behaviour that used to make results unrealistic:
prewarmed containers usable in the same step and never billed, forecasts that
could not be wrong, requests counted several times, parked taxis issuing
requests forever, energy integrated over 1 s per 60 s step, and so on.
"""
import pytest

from central_node.control_layer.controller_module.get_all_users_controller import GetAllUsersController
from central_node.control_layer.scheduler_module.scheduler import AssignmentAlgorithm
from config import Config
from shared.resource_layer.warm_pool import WarmPoolManager

from conftest import make_user


# ---------------------------------------------------------------- warm pool
def test_prewarm_is_not_usable_in_the_step_it_is_launched():
    pool = WarmPoolManager(ttl_steps=10, max_warm_per_edge=4)

    assert pool.prewarm("edge_001", "fn", now=5, ready_delay=1) is True

    assert pool.lookup("edge_001", "fn", now=5) is False
    assert pool.lookup("edge_001", "fn", now=6) is True
    assert (pool.prewarm_launches, pool.prewarm_hits, pool.prewarm_wasted) == (1, 1, 0)


def test_prewarm_is_a_noop_when_container_is_already_live():
    pool = WarmPoolManager(ttl_steps=10, max_warm_per_edge=4)
    pool.admit_cold("edge_001", "fn", now=1)

    assert pool.prewarm("edge_001", "fn", now=2) is False
    assert pool.prewarm_launches == 0


def test_unused_prewarm_is_counted_as_wasted_when_it_expires():
    pool = WarmPoolManager(ttl_steps=3, max_warm_per_edge=4)
    pool.prewarm("edge_001", "fn", now=0, ready_delay=1)

    assert pool.size("edge_001", now=10) == 0
    assert pool.prewarm_wasted == 1


def test_keep_alive_is_billed_for_ttl_steps_after_last_use():
    pool = WarmPoolManager(ttl_steps=3, max_warm_per_edge=4)
    pool.admit_cold("edge_001", "fn", now=0)

    assert [pool.total_retained(now=t) for t in range(5)] == [1, 1, 1, 0, 0]


def test_no_keep_alive_means_nothing_is_retained():
    pool = WarmPoolManager(ttl_steps=0, max_warm_per_edge=4)
    pool.admit_cold("edge_001", "fn", now=0)

    assert pool.total_retained(now=0) == 0


def test_request_during_prewarm_launch_is_cold_and_launch_is_wasted():
    pool = WarmPoolManager(ttl_steps=10, max_warm_per_edge=4)
    pool.prewarm("edge_001", "fn", now=5, ready_delay=1)

    warm = pool.lookup("edge_001", "fn", now=5)
    if not warm:
        pool.admit_cold("edge_001", "fn", now=5)

    assert warm is False
    assert pool.prewarm_wasted == 1


# ---------------------------------------------------------------- replay harness
def _replay(scheduler, algorithm, trajectories, steps):
    """Run the TaxiD replay loop for `steps` steps; return per-step breakdowns."""
    scheduler.set_assignment_algorithm(algorithm.value)
    scheduler.warm_pool.reset()
    scheduler.set_current_dataset("taxiD_Replay")
    scheduler.set_trajectories_px(trajectories)
    scheduler.set_current_step_id(0)
    for uid, seq in trajectories.items():
        user = make_user(uid, seq[0]["x"], seq[0]["y"])
        scheduler.create_user_node(user)
        user.history = []
    scheduler.node_assignment()
    scheduler.simulation = True

    out = []
    for _ in range(steps):
        GetAllUsersController(scheduler, data_manager=None).execute()
        out.append(scheduler.calculate_turnaround_time_breakdown())
    return out


def _jump_trajectory():
    # 30 min next to edge_001 (100,100), then 10 min next to edge_002 (500,100).
    return [{"ts": i * 60.0, "x": 120.0, "y": 100.0} for i in range(30)] + [
        {"ts": i * 60.0, "x": 480.0, "y": 100.0} for i in range(30, 40)
    ]


def test_oracle_prewarm_makes_the_handoff_warm(scheduler):
    steps = _replay(scheduler, AssignmentAlgorithm.PREWARM_ORACLE, {"user_a": _jump_trajectory()}, 32)

    # Step id 31 = first request at edge_002 (trajectory index 30).
    handoff = steps[30]
    assert scheduler.user_nodes["user_a"].assigned_node_id == "edge_002"
    assert handoff["warm_count"] == 1 and handoff["cold_count"] == 0
    assert scheduler.warm_pool.prewarm_hits == 1


def test_forecast_counters_record_moves_to_another_cloudlet(scheduler):
    steps = _replay(scheduler, AssignmentAlgorithm.PREWARM_ORACLE, {"user_a": _jump_trajectory()}, 30)

    # Planning ticks at step ids 20, 25, 30; only the tick at 30 sees the jump.
    assert sum(s["forecasts"] for s in steps) == 3
    assert sum(s["forecast_moves"] for s in steps) == 1


def test_persistence_forecast_cannot_anticipate_the_handoff(scheduler):
    steps = _replay(scheduler, AssignmentAlgorithm.PREWARM_PERSISTENCE, {"user_a": _jump_trajectory()}, 32)

    handoff = steps[30]
    assert handoff["cold_count"] == 1
    assert scheduler.warm_pool.prewarm_launches == 0


def test_prewarm_variants_serve_at_nearest_cloudlet_not_at_forecast(scheduler):
    _replay(scheduler, AssignmentAlgorithm.PREWARM_ORACLE, {"user_a": _jump_trajectory()}, 30)

    # Step id 30: oracle already forecasts edge_002, but the user is still next
    # to edge_001 and must be served there.
    assert scheduler.user_nodes["user_a"].assigned_node_id == "edge_001"


def test_departed_users_stop_issuing_requests(scheduler):
    short = [{"ts": i * 60.0, "x": 120.0, "y": 100.0} for i in range(3)]
    steps = _replay(scheduler, AssignmentAlgorithm.GREEDY_KEEPALIVE, {"user_a": short}, 6)

    assert [s["requests"] for s in steps] == [1, 1, 1, 0, 0, 0]
    assert "user_a" not in scheduler.user_nodes


def test_replay_history_has_no_duplicated_first_point(scheduler):
    traj = [{"ts": i * 60.0, "x": 120.0 + i, "y": 100.0} for i in range(5)]
    _replay(scheduler, AssignmentAlgorithm.GREEDY_KEEPALIVE, {"user_a": traj}, 3)

    xs = [round(p["x"] / Config.DEFAULT_PIXEL_TO_METERS) for p in scheduler.user_nodes["user_a"].history]
    assert xs == [120, 121, 122]


# ---------------------------------------------------------------- request counting
def test_only_requests_of_the_current_step_are_counted(populated_scheduler, monkeypatch):
    monkeypatch.setattr(Config, "REQUEST_INTERVAL_STEPS", 5)
    sched = populated_scheduler
    sched.set_assignment_algorithm(AssignmentAlgorithm.GREEDY_KEEPALIVE.value)
    sched.node_assignment()
    sched.simulation = True
    sched.set_current_dataset("none")

    counted = []
    for step in range(1, 11):
        sched.set_current_step_id(step)
        ctrl = GetAllUsersController(sched, data_manager=None)
        ctrl.execute()
        counted.append(int(sched.calculate_turnaround_time_breakdown()["requests"]))

    n = len(sched.user_nodes)
    assert counted == [0, 0, 0, 0, n, 0, 0, 0, 0, n]


# ---------------------------------------------------------------- capacity
def test_prewarm_variants_account_every_user_against_edge_capacity(populated_scheduler):
    sched = populated_scheduler
    sched.set_assignment_algorithm(AssignmentAlgorithm.PREWARM_ORACLE.value)
    sched.set_current_step_id(1)
    sched.node_assignment()

    assert sum(sched._assigned_concurrency.values()) == len(sched.user_nodes)


# ---------------------------------------------------------------- latency
def test_handoff_migration_uses_backhaul_and_is_charged_to_next_request(scheduler):
    user = make_user("user_a", 110.0, 100.0)
    user.data_size_demand = 512 * 1024
    scheduler.create_user_node(user)
    scheduler._apply_assignment_latency(user, "edge_001")
    scheduler._apply_assignment_latency(user, "edge_002")

    expected = 512 * 1024 / Config.BACKHAUL_BANDWIDTH_BYTES_PER_MS
    assert user.pending_migration_ms == pytest.approx(expected)
    assert expected < 10.0  # ~4 ms over 1 Gbps, not ~175 ms over 4G


def test_central_cloud_pays_wan_latency(scheduler):
    loc = dict(scheduler.central_node["location"])
    scheduler.edge_nodes["edge_001"].location = dict(loc)

    _, edge_ms = scheduler._node_propagation_delay(loc, "edge_001")
    _, central_ms = scheduler._node_propagation_delay(loc, "central_node")

    assert central_ms - edge_ms == pytest.approx(Config.CENTRAL_WAN_EXTRA_MS)


# ---------------------------------------------------------------- energy
def _energy(**kw):
    from shared.resource_layer.energy_model import EnergyModel

    base = dict(num_edge_nodes=10, num_users=0, avg_edge_cpu_util=0.0,
                avg_data_size_bytes=512 * 1024, avg_bandwidth_bytes_per_s=3e6)
    base.update(kw)
    return EnergyModel().estimate_timestep_energy(**base)


def test_static_energy_is_integrated_over_the_step_duration():
    one_s = _energy(timestep_duration_s=1.0)["static_energy_j"]
    sixty_s = _energy(timestep_duration_s=60.0)["static_energy_j"]

    assert sixty_s == pytest.approx(60 * one_s, rel=1e-3)


def test_idle_and_prewarmed_containers_cost_energy():
    idle = _energy(live_containers=0)
    kept = _energy(live_containers=100)
    prewarmed = _energy(prewarm_launches=10)

    assert kept["keepalive_energy_j"] == pytest.approx(100 * Config.CONTAINER_IDLE_POWER_W * 60.0, rel=1e-3)
    assert kept["total_energy_j"] > idle["total_energy_j"]
    assert prewarmed["prewarm_energy_j"] > 0
    assert prewarmed["total_energy_j"] > idle["total_energy_j"]


def test_cold_request_pays_execution_plus_cold_start():
    warm = _energy(edge_warm=1)
    cold = _energy(edge_cold=1)

    assert cold["execution_energy_j"] == pytest.approx(warm["execution_energy_j"])
    assert cold["variable_energy_j"] > warm["variable_energy_j"]


def test_power_profile_does_not_depend_on_host():
    from shared.resource_layer.energy_model import SystemPowerProfile

    edge = SystemPowerProfile.for_simulation(is_edge=True)

    assert edge.get_total_idle_power() == pytest.approx(
        Config.EDGE_CPU_IDLE_W + Config.EDGE_MEMORY_W + Config.EDGE_STORAGE_W + Config.EDGE_BASE_W
    )
