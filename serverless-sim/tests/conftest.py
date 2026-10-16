"""Shared fixtures for the serverless-sim test suite.

The suite targets the pure-python simulation core (scheduler, warm pool,
controllers) so it runs without Docker, without a live Flask server and
without the PyTorch predictor artifacts.
"""
import sys
import time
from pathlib import Path

import pytest

# serverless-sim/ must be importable as the package root ("from config import Config").
SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from central_node.control_layer.models import EdgeNodeInfo, Latency, NodeMetrics, UserNodeInfo  # noqa: E402


def make_metrics(node_id: str, memory_total: int = 8 * 1024**3) -> NodeMetrics:
    return NodeMetrics(
        node_id=node_id,
        cpu_usage=10.0,
        memory_usage=10.0,
        memory_total=memory_total,
        running_container=0,
        warm_container=0,
        active_requests=0,
        total_requests=0,
        response_time_avg=0.0,
        energy_consumption=0.0,
        load_average=[0.0, 0.0, 0.0],
        network_io={},
        disk_io={},
        timestamp=time.time(),
        uptime=0.0,
    )


def make_edge(node_id: str, x: float, y: float) -> EdgeNodeInfo:
    return EdgeNodeInfo(
        node_id=node_id,
        endpoint=f"localhost:9{node_id[-3:]}",
        location={"x": x, "y": y},
        system_info={},
        last_heartbeat=time.time(),
        metrics_info=make_metrics(node_id),
        coverage=1000.0,
    )


def make_user(user_id: str, x: float, y: float) -> UserNodeInfo:
    latency = Latency(
        distance=0.0,
        data_size=512 * 1024,
        bandwidth=3000.0,
        propagation_delay=0.0,
        transmission_delay=512 * 1024 / 3000.0,
        computation_delay=0.0,
        container_status="unknown",
        total_turnaround_time=0.0,
    )
    return UserNodeInfo(
        user_id=user_id,
        assigned_node_id=None,
        location={"x": x, "y": y},
        size=10,
        speed=5,
        last_executed=0,
        latency=latency,
    )


@pytest.fixture
def scheduler():
    """A scheduler with 3 edge nodes and no predictor loaded."""
    from central_node.control_layer.scheduler_module.scheduler import Scheduler

    sched = Scheduler()
    for i, (x, y) in enumerate([(100.0, 100.0), (500.0, 100.0), (300.0, 400.0)], start=1):
        sched.register_edge_node(make_edge(f"edge_{i:03d}", x, y))
    sched.predictor_adapter = None
    return sched


@pytest.fixture
def populated_scheduler(scheduler):
    """Scheduler above, plus 6 users spread across the map."""
    for i, (x, y) in enumerate(
        [(110.0, 105.0), (120.0, 95.0), (505.0, 110.0), (495.0, 90.0), (305.0, 405.0), (295.0, 395.0)],
        start=1,
    ):
        scheduler.create_user_node(make_user(f"user_{i}", x, y))
    return scheduler
