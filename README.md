# Serverless Edge Computing Simulation

A comprehensive simulation platform for serverless edge computing environments, featuring distributed container orchestration, real-time performance monitoring, and intelligent workload management across multiple nodes.

## 🚀 Key Features

### 🎯 Core Simulation Capabilities

- **Multi-Node Architecture**: Distributed simulation across central and edge nodes
- **Container Orchestration**: Docker-based serverless function execution
- **Real-Time Monitoring**: Live performance metrics and system health tracking
- **Interactive Visualization**: Canvas-based network topology and metrics display

### 🧠 Intelligent Workload Management

- **ML-Based Prediction**: LSTM models for workload forecasting
- **Dynamic Scheduling**: Load-aware request routing and resource allocation
- **Container Migration**: Intelligent migration between edge nodes
- **Cold Start Optimization**: Efficient container lifecycle management

### 📊 Container State Management

The system manages four distinct container states:

- **INIT**: `docker create` - Container created but not started (cold state)
- **RUNNING**: `docker run` - Container actively executing requests
- **WARM**: `docker stop` - Container stopped but available for reuse  (warm state)
- **DEAD**: `docker rm` - Container removed from system



## 🛠️ Technology Stack


### Infrastructure

- **Docker**: Containerization platform
- **Multi-node Networking**: Distributed deployment support
- **Real-time Communication**: WebSocket-style updates

## 📋 Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: Version 3.8 or higher
- **Node.js**: Version 16 or higher  
- **Docker**: Latest stable version
- **RAM**: Minimum 4GB, recommended 8GB+
- **Network**: All nodes must be on the same network

### Software Dependencies

- pip3 package manager
- npm/yarn package manager
- Git version control
- Docker daemon running

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/truongng201/Serverless-edge-computing-simulation.git
cd Serverless-edge-computing-simulation
```

### 2. Setup Backend

```bash
cd serverless-sim
pip install -r requirements.txt

# Configure environment
cp central_config.env.example central_config.env
cp edge_config.env.example edge_config.env
# Edit configuration files as needed
```

### 3. Setup Frontend

```bash
cd ../simulation-ui
npm install
```

### 4. Deploy Central Node

```bash
cd ../serverless-sim
./deploy_central.sh
```

### 5. Deploy Edge Nodes

```bash
# On each edge machine:
cd ../serverless-sim
./deploy_edge.sh --node-id edge_<index> --central-url http://CENTRAL_IP:8000 --port <port>
```

### 6. Start Web Interface

```bash
cd ../simulation-ui  
npm run dev
# Access at http://localhost:3000
```

## 🔧 Configuration

### Central Node Configuration (`central_config.env`)

```env
NODE_TYPE=central
PORT=5001
LOG_LEVEL=INFO
METRICS_INTERVAL=10
PREDICTION_MODEL=lstm
ENABLE_MIGRATION=true
```

### Edge Node Configuration (`edge_config.env`)

```env
NODE_TYPE=edge
NODE_ID=edge_001
CENTRAL_URL=http://192.168.1.100:5001
PORT=5002
CONTAINER_MEMORY_LIMIT=256m
```

## 🎮 Usage Guide

### Web Interface Controls

1. **Simulation Control**: Start/stop simulation
2. **Node Management**: Add/remove edge nodes dynamically  
3. **User Management**: Generate users with mobility patterns
4. **Metrics Monitoring**: Real-time performance dashboards
5. **Algorithm Selection**: Choose placement and scheduling algorithms

### API Endpoints

#### Central Node API (`/api/v1/central/`)

- `POST /nodes/register` - Register new edge node
- `GET /metrics/global` - Get cluster-wide metrics
- `POST /migrate` - Trigger container migration
- `GET /topology` - Get network topology

#### Edge Node API (`/api/v1/edge/`)

- `POST /containers/execute` - Execute serverless function
- `GET /metrics/local` - Get local node metrics
- `GET /status` - Get node health status

## 📊 Monitoring & Metrics

### System Metrics (Collected every 10 seconds)

- **CPU Usage**: Per-core utilization percentages
- **Memory**: Available, used, and cached memory
- **Network**: Bandwidth utilization and packet counts
- **Energy**: Power consumption calculations
- **Container**: State transitions and execution times

### Performance Metrics

- **Response Time**: End-to-end request processing
- **Throughput**: Requests processed per second
- **Cold Start Latency**: Container initialization time
- **Migration Time**: Container migration duration
- **Resource Utilization**: CPU, memory, and network efficiency

## 🧪 Testing & Validation

### Test Network Connectivity

```bash
./test_network.sh
```

### Monitor Cluster Health

```bash  
./monitor_cluster.sh
```

## 🔬 Research Applications

### Academic Use Cases

- **Edge Computing Research**: Distributed system performance analysis
- **Serverless Computing**: Cold start optimization studies
- **Container Orchestration**: Migration strategy evaluation
- **ML in Edge**: Predictive scheduling algorithm development
- **Energy Efficiency**: Green computing optimization research

### Experimental Scenarios

- Multi-tier edge hierarchies
- Heterogeneous resource environments  
- Dynamic workload patterns
- Network partition tolerance
- User mobility modeling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**📚 For detailed deployment instructions, see [DEPLOYMENT.md](serverless-sim/DEPLOYMENT.md)**

**🔧 For backend architecture details, see [serverless-sim/README.md](serverless-sim/README.md)**
