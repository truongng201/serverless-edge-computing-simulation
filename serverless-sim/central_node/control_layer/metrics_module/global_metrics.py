from typing import Dict, List
from dataclasses import dataclass, asdict

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