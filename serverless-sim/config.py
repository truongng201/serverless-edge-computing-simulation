from enum import Enum

class ContainerState(Enum):
    COLD_START = "cold_start"  # docker create [container]
    RUNNING = "running"        # docker start [container]
    IDLE = "idle"             # docker stop [container]
    DEAD = "dead"             # docker rm [container]

class NodeType(Enum):
    CENTRAL = "central"
    EDGE = "edge"

class Config:
    # Container Configuration
    DEFAULT_CONTAINER_IMAGE = "serverless-handler:latest"
    DEFAULT_CONTAINER_COMMAND = "sleep infinity"
    DEFAULT_CONTAINER_DETACH_MODE = True
    DEFAULT_CONTAINER_MEMORY_LIMIT = "256m"  # 256 MB
    
    # Metrics Collection
    METRICS_COLLECTION_INTERVAL = 10  # seconds
    
    # Node Configuration
    CENTRAL_NODE_PORT = 5001
    EDGE_NODE_PORT_RANGE = (5002, 5020)
    
    # API Endpoints
    CENTRAL_API_PREFIX = "/api/v1/central"
    EDGE_API_PREFIX = "/api/v1/edge"
    
    # Scheduling Configuration
    DEFAULT_SCHEDULING_ALGORITHM = "round_robin"
    MIGRATION_THRESHOLD = 0.8  # CPU usage threshold for migration
    
    # Docker Configuration
    DOCKER_SOCKET = "unix://var/run/docker.sock"
    CONTAINER_NETWORK = "serverless-network"