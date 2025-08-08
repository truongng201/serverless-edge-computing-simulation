# Serverless Edge Computing Simulation - Core Architecture

This document describes the serverless module core architecture with support for both Central and Edge nodes.

## Architecture Overview

The system is designed with a hierarchical architecture:

### Central Node (3 layers)

1. **Control Layer**: High-level orchestration and management
   - Scheduler module for request routing and load balancing
   - Prediction module for workload forecasting using ML models
   - Migration module for container migration between nodes
   - Global metrics collection for cluster-wide monitoring
   - Graph visualizer for cluster topology visualization

2. **API Layer**: Request processing and coordination
   - Processes requests from simulation UI
   - Coordinates with control layer components
   - Manages edge node registration and communication

3. **Resource Layer**: Same as edge nodes (Docker management)
   - Docker container lifecycle management
   - System metrics collection from /proc files

### Edge Node (2 layers)

1. **API Layer**: Container execution and request handling
   - Identifies cold start vs warm start scenarios
   - Runs containers (replicas) and manages their lifecycle
   - Handles logging and resource monitoring

2. **Resource Layer**: Docker daemon interaction and system metrics
   - Direct interaction with Docker daemon API
   - Real-time system metrics collection
   - Energy consumption calculations

## Container State Management

The system manages containers through these states using Docker daemon API:

- **COLD_START**: `docker create [container]` - Container created but not started
- **RUNNING**: `docker start [container]` - Container actively executing
- **IDLE**: `docker stop [container]` - Container stopped but available for reuse
- **DEAD**: `docker rm [container]` - Container removed from system

## Metrics Collection

System metrics are collected every 10 seconds:

- **CPU usage**: Reading from `/proc/stat`
- **Memory usage**: Reading from `/proc/meminfo`
- **Network I/O**: Reading from `/proc/net/dev`
- **Disk I/O**: Reading from `/proc/diskstats`
- **CPU Energy (kWh)**: Calculated as `usage (kW) × vCPUHours (h)`

## Directory Structure

``` plaintext
serverless-sim/
├── main.py                 # Entry point supporting both node types
├── config.py              # Configuration and enums
├── requirements.txt       # Dependencies
├── README.md              # This file
├── central_node/          # Central node implementation
│   ├── control_layer/     # First layer - Control and orchestration
│   │   ├── scheduler.py            # Request scheduling and load balancing
│   │   ├── prediction.py           # Workload prediction using ML models
│   │   ├── migration.py            # Container migration management
│   │   ├── global_metrics.py       # Cluster-wide metrics collection
│   │   ├── graph_visualizer.py     # Graph-based cluster visualization
│   │   ├── data_manager.py         # Simulation data management
│   │   └── ui_handler.py           # UI requests and legacy compatibility
│   ├── api_layer/         # Second layer - API processing
│   │   └── central_api.py          # Central node REST API
│   └── resource_layer/    # Third layer - Same as edge nodes
├── edge_node/             # Edge node implementation (Cloudlet nodes)
│   ├── api_layer/         # First layer - Request processing
│   │   └── edge_api.py             # Edge node REST API
│   └── resource_layer/    # Second layer - Docker and metrics
├── shared/                # Shared components
│   ├── docker_manager.py           # Docker container lifecycle management
│   └── system_metrics.py           # System metrics collection (/proc files)
```

## Component Details

### Central Node - Control Layer

#### Scheduler (`scheduler.py`)

- **Purpose**: Decides which edge node should handle each request
- **Strategies**: Round Robin, Least Loaded, Geographic, Predictive
- **Features**:
  - Edge node registration and health monitoring
  - Load balancing across cluster
  - Request routing decisions
  - Receives cloudlet (edge node) requests

#### Prediction Module (`prediction.py`)

- **Purpose**: Predicts future workloads and resource requirements
- **Features**:
  - Time series analysis of historical data
  - Machine learning models for load prediction
  - Performance forecasting
  - Model training and accuracy tracking

#### Migration Manager (`migration.py`)

- **Purpose**: Handles container migration between edge nodes
- **Triggers**: High load, resource shortage, node failure, load balancing
- **Features**:
  - Migration decision logic
  - Live migration execution
  - Rollback on failure
  - Migration statistics

#### Global Metrics Collector (`global_metrics.py`)

- **Purpose**: Aggregates metrics from all edge nodes
- **Features**:
  - Real-time cluster monitoring
  - Health status tracking
  - Metrics history and analytics
  - Data export capabilities

#### Graph Visualizer (`graph_visualizer.py`)

- **Purpose**: Provides visual representation of cluster topology
- **Features**:
  - Node and edge visualization
  - Force-directed layout algorithms
  - Real-time cluster state representation
  - Interactive graph data

#### Data Manager (`data_manager.py`)

- **Purpose**: Manages simulation datasets (DACT and vehicle data)
- **Features**:
  - CSV data loading and preprocessing
  - Coordinate normalization
  - Timestep-based data retrieval
  - Support for multiple data formats

#### UI Handler (`ui_handler.py`)

- **Purpose**: Handles simulation UI requests and legacy compatibility
- **Features**:
  - Vehicle and DACT data endpoints
  - Simulation control (start/stop)
  - Status monitoring
  - Legacy Flask endpoint compatibility

### API Layers

#### Central Node API (`central_api.py`)

- **Purpose**: Process requests from control layer of central node and simulation UI
- **Endpoints**:
  - `POST /api/v1/central/schedule` - Schedule requests
  - `POST /api/v1/central/nodes/register` - Register edge nodes
  - `POST /api/v1/central/nodes/{id}/metrics` - Receive metrics
  - `GET /api/v1/central/cluster/status` - Cluster status
  - `GET /api/v1/central/predict/{node_id}` - Workload predictions
  - `GET /` - Simulation UI home
  - `GET /get_sample` - Vehicle data by timestep (legacy compatibility)
  - `GET /get_dact_sample` - DACT data by step ID
  - `GET /simulation/status` - Simulation status
  - `POST /simulation/start` - Start simulation
  - `POST /simulation/stop` - Stop simulation
  - Graph visualization endpoints

#### Edge Node API (`edge_api.py`)

- **Purpose**: Process requests from control layer of central node
- **Features**:
  - Identify cold start and warm start replicas
  - Run containers (replicas)
  - Kill containers
  - Logging and monitoring
- **Endpoints**:
  - `POST /api/v1/edge/execute` - Execute functions
  - `GET /api/v1/edge/status` - Node status
  - `GET /api/v1/edge/containers` - List containers
  - `GET /api/v1/edge/containers/{id}/stats` - Container stats
  - `POST /api/v1/edge/cleanup` - Clean up idle containers

### Resource Layer (Shared)

#### Docker Manager (`docker_manager.py`)

- **Container State Management**:
  - `COLD_START`: `docker create [container]`
  - `RUNNING`: `docker start [container]`
  - `IDLE`: `docker stop [container]`
  - `DEAD`: `docker rm [container]`
- **Features**:
  - Full container lifecycle management
  - Real-time container statistics
  - Resource monitoring
  - Direct Docker daemon API interaction

#### System Metrics Collector (`system_metrics.py`)

- **Metrics Sources**:
  - CPU usage: `/proc/stat`
  - Memory usage: `/proc/meminfo`
  - Network I/O: `/proc/net/dev`
  - Disk I/O: `/proc/diskstats`
- **Calculations**:
  - CPU Energy (kWh) = usage (kW) × vCPUHours (h)
  - Collection interval: 10 seconds
- **Real-time Server Metrics**: Provides predefined state metrics for simulation

## Usage

### Starting Central Node

```bash
cd serverless-sim
python main.py --mode central --port 5001
```

### Starting Edge Nodes (Cloudlet Nodes)

```bash
# Edge Node 1
python main.py --mode edge --node-id edge_001 --port 5002 --central-url http://localhost:5001

# Edge Node 2
python main.py --mode edge --node-id edge_002 --port 5003 --central-url http://localhost:5001
```

### Command Line Options

- `--mode`: Node type (`central` or `edge`)
- `--node-id`: Unique identifier for edge nodes
- `--central-url`: Central node URL (for edge nodes)
- `--port`: Port to run on
- `--host`: Host to bind to (default: 0.0.0.0)
- `--debug`: Enable debug mode
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)

## API Examples

### Schedule a Request (Central Node)

```bash
curl -X POST http://localhost:5001/api/v1/central/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "hello_world",
    "payload": {"message": "Hello"},
    "requirements": {"cpu": 0.5, "memory": "256M"}
  }'
```

### Execute Function (Edge Node)

```bash
curl -X POST http://localhost:5002/api/v1/edge/execute \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "hello_world",
    "image": "my-function:latest",
    "environment": {"ENV": "production"}
  }'
```

### Get Cluster Status

```bash
curl http://localhost:5001/api/v1/central/cluster/status
```

### Get Simulation Data (Legacy UI Compatibility)

```bash
# Get vehicle data for timestep
curl "http://localhost:5001/get_sample?timestep=28800.00"

# Get DACT data for step
curl "http://localhost:5001/get_dact_sample?step_id=1"

# Get simulation status
curl http://localhost:5001/simulation/status
```

## Configuration

Key configuration options in `config.py`:

```python
# Container States
COLD_START, RUNNING, IDLE, DEAD

# Metrics Collection
METRICS_COLLECTION_INTERVAL = 10  # seconds

# Ports
CENTRAL_NODE_PORT = 5001
EDGE_NODE_PORT_RANGE = (5002, 5020)

# Migration
MIGRATION_THRESHOLD = 0.8  # CPU usage threshold
```

## Integration with Simulation UI

The central node supports the simulation UI through the integrated UI handler in the control layer. The UI endpoints are available at the root level for legacy compatibility, while the new API endpoints are available under `/api/v1/central/` prefix. This provides seamless integration between the control layer components and the simulation interface.

## Monitoring and Metrics

### Real-time Metrics

- CPU usage, memory usage, network I/O, disk I/O
- Container states and resource consumption
- Request latency and throughput
- Energy consumption calculations

### Cluster Analytics

- Load distribution across nodes
- Migration patterns and success rates
- Prediction accuracy
- Health status monitoring

### Data Export

Metrics can be exported in JSON format:

```bash
curl "http://localhost:5001/api/v1/central/metrics/export?duration_hours=1&format=json"
```

This architecture provides a comprehensive serverless edge computing simulation with clear separation between Central Node control capabilities and Edge Node execution capabilities, matching the requirements for both cloudlet (edge) and central node functionality.

```bash
git clone <repository-url>
```

- Navigate to the project directory:

```bash
cd serverless-sim
```

- Activate the virtual environment:

```bash
conda create -n serverless-sim python=3.11 pip
conda activate serverless-sim
```

- Install the required packages:

```bash
pip install -r requirements.txt
```

```bash
python main.py
```
