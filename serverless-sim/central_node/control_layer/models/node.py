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
    history: List[Dict[str, float]] = field(default_factory=list)
    # Optimization parameters
    bandwidth_demand: float = 10.0    # Ï‰_i^t (Mbps)
    memory_demand: float = Config.DEFAULT_USER_MEMORY_DEMAND
    cpu_demand: float = 1.0           # Ï€_i^t (cores)
    data_size_demand: float = 1024.0  # s_i^t (bytes) - also migration data
    previous_node_id: Optional[str] = None  # For migration tracking
    migration_cost: float = 0.0       # Current migration cost
    cold_start_penalty: float = 0.0   # Cold start penalty
    # Simulated execution / prewarm bookkeeping
    last_executed_node_id: Optional[str] = None
    last_executed_step_id: Optional[int] = None
    planned_node_id: Optional[str] = None
    planned_step_id: Optional[int] = None
