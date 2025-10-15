from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

class MigrationReason(Enum):
    HIGH_LOAD = "high_load"
    RESOURCE_SHORTAGE = "resource_shortage"
    NETWORK_LATENCY = "network_latency"
    NODE_FAILURE = "node_failure"
    LOAD_BALANCING = "load_balancing"

@dataclass
class MigrationRequest:
    container_id: str
    source_node_id: str
    target_node_id: str
    reason: MigrationReason
    priority: int  # 1-10, 10 being highest
    estimated_downtime: float  # seconds
    request_time: float

@dataclass
class MigrationStatus:
    request_id: str
    status: str  # pending, in_progress, completed, failed
    progress: float  # 0.0 to 1.0
    start_time: Optional[float]
    end_time: Optional[float]
    error_message: Optional[str]