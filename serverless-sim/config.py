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
    DEFAULT_MAX_WARM_TIME = 8  # seconds: warm time larger than execution time to allow reuse
    
    
    # Cleanup
    CLEANUP_WARM_CONTAINERS_INTERVAL = 5  # seconds
    CLEANUP_DEAD_NODES_INTERVAL = 10  # seconds

    # Metrics Collection
    METRICS_COLLECTION_INTERVAL = 10  # seconds
    
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
    DEFAULT_EXECUTION_TIME_INTERVAL = 10 # seconds: every 5 seconds all user in simulation call it assigned node
    DEFAULT_RANDOM_DATA_SIZE_RANGE_IN_BYTES = (1024, 10240)  # 1 KB to 10 KB
    DEFAULT_RANDOM_BANDWIDTH_RANGE_IN_BYTES_PER_MILLISECOND = (100, 1000)  # 100 B/ms to 1 KB/ms
    DEFAULT_DATA_SIZE_IN_BYTES = 512 * 1024  # 512 KB
    DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND = 512  # 512 B/ms
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

    # Edge node deployment configuration
    EXPECTED_TOTAL_EDGE_NODES = int(os.getenv("EXPECTED_EDGE_NODES", "10"))
    
    # Predictive scheduling parameters
    TDRIVE_ARTIFACT_DIR = os.getenv(
        "TDRIVE_ARTIFACT_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "predict-model-with-taxi",
            "tdrive_predictor_artifacts",
            "phase_b_5k_fast",
        ),
    )
    TDRIVE_CKPT_NAME = os.getenv("TDRIVE_CKPT_NAME", "gru_phase_curv_step.pt")
    TDRIVE_DEVICE = os.getenv("TDRIVE_DEVICE", "cpu")
    TDRIVE_HISTORY_LENGTH = int(os.getenv("TDRIVE_HISTORY_LENGTH", "20"))
    TDRIVE_MAX_RADIUS_M = float(os.getenv("TDRIVE_MAX_RADIUS_M", "1000"))
    TDRIVE_SOFTMAX_TEMPERATURE = float(os.getenv("TDRIVE_SOFTMAX_TEMPERATURE", "50"))
    PREDICTIVE_STOP_SPEED = float(os.getenv("PREDICTIVE_STOP_SPEED", "0.5"))
    PREDICTIVE_DEFAULT_MEMORY_REQUIREMENT_MB = 256  # default per-user memory footprint
    PREDICTIVE_DEFAULT_DATA_SIZE_BYTES = 512 * 1024  # 512 KB when historical data missing
    PREDICTIVE_COLD_START_MS = 300  # expected cold start penalty
    PREDICTIVE_HANDOFF_COST = 0.05  # score penalty for handoff
    PREDICTIVE_WARM_BASE_PROB = 0.2  # base warm probability when metrics are missing

    # Dataset playback speed (Scenario 2 / vehicles)
    # Multiply timestep advancement per poll to make movements appear faster on canvas
    DATASET_STEP_MULTIPLIER = 8
    
    # User Movement Configuration
    USER_MIN_SPEED = 1  # m/s - minimum user movement speed (walking speed)
    USER_MAX_SPEED = 3  # m/s - maximum user movement speed (slow jogging)
    USER_MAX_DISTANCE_FROM_CENTER = 800  # meters - maximum distance from cluster center
    USER_MAX_SPAWN_DISTANCE = 600  # meters - initial spawn radius around center
    USER_MIN_SPAWN_DISTANCE = 100  # meters - minimum spawn distance from center
    
    # User
    DEFAULT_USER_MEMORY_DEMAND = 134217728 # 128 MB

    # TaxiD (Beijing OSM) scenario
    # Path to the OSM XML for Beijing bounding box used by TaxiD scenario
    TAXID_OSM_XML_PATH = os.getenv(
        "TAXID_OSM_XML_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "predict-model-with-taxi",
            "planet_116.127,39.756_116.813,40.084.osm",
            "planet_116.127,39.756_116.813,40.084.osm",
        ),
    )
    # Optional GraphML cache (speeds up repeated loads if present)
    TAXID_GRAPHML_PATH = os.getenv(
        "TAXID_GRAPHML_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "predict-model-with-taxi",
            "osm",
            "beijing_taxid.graphml",
        ),
    )
    # Initial viewport for mapping meters->pixels (used for road rendering)
    # ACTUAL Beijing TaxiD map bounds: 58782m x 36695m = 5878px x 3670px
    TAXID_VIEWPORT_WIDTH_PX = int(os.getenv("TAXID_VIEWPORT_WIDTH_PX", "5878"))
    TAXID_VIEWPORT_HEIGHT_PX = int(os.getenv("TAXID_VIEWPORT_HEIGHT_PX", "3670"))
    TAXID_VIEWPORT_MARGIN_PX = int(os.getenv("TAXID_VIEWPORT_MARGIN_PX", "200"))

    # Preprocessed roads JSON (gz) path for fast UI serving
    TAXID_ROADS_JSON_GZ_PATH = os.getenv(
        "TAXID_ROADS_JSON_GZ_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "predict-model-with-taxi",
            "osm",
            "beijing_taxid_roads.json.gz",
        ),
    )

