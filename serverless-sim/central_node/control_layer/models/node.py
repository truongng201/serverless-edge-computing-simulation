import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from config import Config

@dataclass
class NodeMetrics:
    node_id: str
    cpu_usage: float
    memory_usage: float
    memory_total: int
    running_container: int
    warm_container: int
    active_requests: int
    total_requests: int
    response_time_avg: float
    energy_consumption: float
    load_average: List[float]
    network_io: Dict[str, float]
    disk_io: Dict[str, float]
    timestamp: float
    uptime: float

@dataclass
class Latency:
    distance: float
    data_size: float
    bandwidth: float
    propagation_delay: float
    transmission_delay: float
    computation_delay: float
    container_status: str
    total_turnaround_time: float

@dataclass
class EdgeNodeInfo:
    node_id: str
    endpoint: str
    location: Dict[str, float]  # {"x": ..., "y": ...}
    system_info: Dict[str, Any]
    last_heartbeat: float
    metrics_info: NodeMetrics
    coverage: float

@dataclass
class UserNodeInfo:
    user_id: str
    assigned_node_id: str
    location: Dict[str, float]  # {"x": ..., "y": ...}
    size: int
    speed: int
    last_executed: float
    latency: Latency
    created_at: float = field(default_factory=lambda: time.time())
    last_updated: float = field(default_factory=lambda: time.time())
    memory_requirement: float = field(default_factory=lambda: Config.PREDICTIVE_DEFAULT_MEMORY_REQUIREMENT_MB * 1024 * 1024)
    last_handoff: float = 0.0
    predictive_debug: Optional[Dict[str, Any]] = None