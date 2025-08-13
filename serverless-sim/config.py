from enum import Enum

class ContainerState(Enum):
    INIT = "initialization"   # docker create [container] - cold start
    RUNNING = "running"        # docker run [container]
    IDLE = "idle"             # docker stop [container] - warm start
    DEAD = "dead"             # docker rm [container]

class NodeType(Enum):
    CENTRAL = "central"
    EDGE = "edge"

class Config:
    # Container Configuration
    DEFAULT_CONTAINER_IMAGE = "python-serverless-handler:latest"
    DEFAULT_CONTAINER_DETACH_MODE = True
    DEFAULT_CONTAINER_MEMORY_LIMIT = "256m"  # 256 MB
    DEFAULT_CONTAINER_ID_LENGTH = 12
    DEFAULT_MAX_IDLE_TIME = 10 # seconds
    
    # Metrics Collection
    METRICS_COLLECTION_INTERVAL = 5  # seconds
    
    # Node Configuration
    CENTRAL_NODE_PORT = 8000
    EDGE_NODE_PORT_RANGE = (8001, 8100)

    # API Endpoints
    CENTRAL_API_PREFIX = "/api/v1/central"
    EDGE_API_PREFIX = "/api/v1/edge"
    
    # Scheduling Configuration
    DEFAULT_SCHEDULING_ALGORITHM = "round_robin"
    MIGRATION_THRESHOLD = 0.8  # CPU usage threshold for migration
    
    # Docker Configuration
    DOCKER_SOCKET = "unix://Users/truongnguyen/.docker/run/docker.sock"
    CONTAINER_NETWORK = "serverless-network"