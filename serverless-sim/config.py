from enum import Enum
import os
import platform

class ContainerState(Enum):
    INIT = "init"   # docker create [container] - cold start
    RUNNING = "running"        # docker run [container]
    WARM = "warm"             # docker stop [container] - warm start
    DEAD = "dead"             # docker rm [container]

class NodeType(Enum):
    CENTRAL = "central"
    EDGE = "edge"

class Config:
    # Container Configuration
    DEFAULT_CONTAINER_IMAGE = "python-serverless-handler:latest"
    DEFAULT_CONTAINER_DETACH_MODE = True
    DEFAULT_CONTAINER_COMMAND = "python -u /app/main.py"
    DEFAULT_CONTAINER_MEMORY_LIMIT = "256m"  # 256 MB
    DEFAULT_CONTAINER_ID_LENGTH = 12
    DEFAULT_MAX_WARM_TIME = 5 # seconds
    
    
    # Cleanup
    CLEANUP_WARM_CONTAINERS_INTERVAL = 5  # seconds
    CLEANUP_DEAD_NODES_INTERVAL = 10  # seconds

    # Metrics Collection
    METRICS_COLLECTION_INTERVAL = 5  # seconds
    
    # Node Configuration
    CENTRAL_NODE_PORT = 8000
    EDGE_NODE_PORT_RANGE = (8001, 8100)
    EDGE_NODE_HEARTBEAT_TIMEOUT = 10  # seconds
    EDGE_NODE_UNHEALTHY_CPU_THRESHOLD = 90  # 90% CPU usage
    EDGE_NODE_UNHEALTHY_MEMORY_THRESHOLD = 90  # 90% memory usage
    EDGE_NODE_WARNING_CPU_THRESHOLD = 70  # 70% CPU usage
    EDGE_NODE_WARNING_MEMORY_THRESHOLD = 70  # 70% memory usage

    # API Endpoints
    CENTRAL_ROUTE_PREFIX = "/api/v1/central"
    EDGE_ROUTE_PREFIX = "/api/v1/edge"
    
    # Scheduling Configuration
    DEFAULT_SCHEDULING_ALGORITHM = "round_robin"
    MIGRATION_THRESHOLD = 0.8  # CPU usage threshold for migration
    
    # Docker Configuration
    # Prefer environment variable if provided; otherwise choose OS-appropriate default
    # - Windows (Docker Desktop): use Named Pipe
    # - Others (Linux/macOS): use default Unix socket
    DOCKER_SOCKET = os.getenv("DOCKER_HOST") or (
        "npipe:////./pipe/docker_engine" if platform.system() == "Windows" else "unix:///var/run/docker.sock"
    )
    CONTAINER_NETWORK = "serverless-network"
    
    # User Configuration
    DEFAULT_EXECUTION_TIME_INTERVAL = 15 # seconds: every 3 seconds all user in simulation call it assigned node
    DEFAULT_RANDOM_DATA_SIZE_RANGE_IN_BYTES = (1024, 10240)  # 1 KB to 10 KB
    DEFAULT_RANDOM_BANDWIDTH_RANGE_IN_BYTES_PER_MILLISECOND = (100, 1000)  # 100 B/ms to 1 KB/ms
    DEFAULT_PROPAGATION_SPEED_IN_METERS = 3 * 10**8  # Speed of light in vacuum (m/s)
    DEFAULT_PIXEL_TO_METERS = 10 # 1 pixel = 10 m

    # User cleanup
    # If a user hasn't been updated for this many seconds, remove it
    USER_TTL_SECONDS = 2
    USER_CLEANUP_INTERVAL = 2  # how often to scan for stale users

    # Assignment / handoff parameters
    HANDOFF_MIN_DWELL_SECONDS = 1.0  # minimum time to stay on a node before switching
    HANDOFF_IMPROVEMENT_THRESHOLD = 0.1  # 10% better score required to switch
    ASSIGNMENT_SCAN_INTERVAL = 0.5  # seconds between reassignment scans
    LOAD_AWARE_ALPHA = 1.0  # weight for CPU load in load-aware score
