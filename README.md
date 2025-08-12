# Serverless Edge Computing Simulation

A comprehensive simulation platform for serverless edge computing environments, featuring distributed container orchestration, real-time performance monitoring, and intelligent workload management across multiple nodes.

## 🏗️ System Architecture

This project implements a hierarchical distributed system with two main components:

### Central Node (Control Hub)

- **Control Layer**: Orchestration, scheduling, prediction, and migration management
- **API Layer**: Request processing and edge node coordination  
- **Resource Layer**: Docker container lifecycle management
- **Web UI**: Interactive simulation interface

### Edge Nodes (Execution Units)

- **API Layer**: Container execution and request handling
- **Resource Layer**: Docker daemon interaction and system metrics collection

```
┌─────────────────────────────────────────────────────────────┐
│                     CENTRAL NODE                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  Control Layer  │  │   API Layer     │  │ Web UI      │  │
│  │                 │  │                 │  │             │  │
│  │ • Scheduler     │  │ • Central API   │  │ • Simulation│  │
│  │ • Predictor     │  │ • Edge Coord.   │  │ • Metrics   │  │
│  │ • Migrator      │  │ • Request Proc. │  │ • Control   │  │
│  │ • Metrics       │  │                 │  │             │  │
│  │ • Visualizer    │  │                 │  │             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Resource Layer                           │  │
│  │              • Docker Management                     │  │
│  │              • System Metrics                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Network Communication
                              │
┌─────────────────────────────────────────────────────────────┐
│                     EDGE NODES                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   API Layer     │  │ Resource Layer  │                  │
│  │                 │  │                 │                  │
│  │ • Request Handle│  │ • Docker API    │                  │
│  │ • Container Mgmt│  │ • System Metrics│                  │
│  │ • Cold/Warm     │  │ • Energy Calc   │                  │
│  │ • Lifecycle     │  │                 │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Project Structure

### Root Directory
```
📁 Serverless-edge-computing-simulation/
├── 📁 serverless-sim/          # Core simulation backend
├── 📁 simulation-ui/           # Next.js frontend interface
└── 📄 README.md               # This documentation
```

### Backend (`serverless-sim/`)
```
📁 serverless-sim/
├── 📄 main.py                 # Application entry point
├── 📄 config.py               # System configuration
├── 📄 requirements.txt        # Python dependencies
├── 📄 central_main.py         # Central node launcher
├── 📄 edge_main.py           # Edge node launcher
├── 📄 DEPLOYMENT.md          # Deployment instructions
├── 📄 README.md              # Backend documentation
├── 📄 *.sh                   # Deployment scripts
├── 📄 *.env.example          # Configuration templates
│
├── 📁 central_node/          # Central node implementation
│   ├── 📁 api_layer/         
│   │   └── 📄 central_api.py # Central API endpoints
│   ├── 📁 control_layer/     # Core orchestration logic
│   │   ├── 📄 scheduler.py   # Load balancing & routing
│   │   ├── 📄 prediction.py  # ML-based workload prediction
│   │   ├── 📄 migration.py   # Container migration logic
│   │   ├── 📄 global_metrics.py # Cluster-wide monitoring
│   │   ├── 📄 graph_visualizer.py # Network topology viz
│   │   ├── 📄 data_manager.py # Data persistence
│   │   ├── 📄 ui_handler.py  # Web UI backend
│   │   ├── 📁 mock_data/     # Test datasets
│   │   └── 📁 prediction_model/ # ML model artifacts
│   └── 📁 resource_layer/    # Docker & system management
│
├── 📁 edge_node/            # Edge node implementation  
│   ├── 📁 api_layer/
│   │   └── 📄 edge_api.py   # Edge API endpoints
│   └── 📁 resource_layer/   # Local resource management
│
└── 📁 shared_resource_layer/              # shared_resource_layer
    ├── 📄 docker_manager.py # Docker operations
    └── 📄 system_metrics.py # System monitoring
```

### Frontend (`simulation-ui/`)
```
📁 simulation-ui/
├── 📄 package.json           # Node.js dependencies
├── 📄 next.config.mjs        # Next.js configuration
├── 📄 tailwind.config.js     # Tailwind CSS config
├── 📄 digital-twin-simulation.jsx # Main simulation component
│
├── 📁 app/                   # Next.js app structure
│   ├── 📄 layout.jsx         # Root layout
│   ├── 📄 page.jsx          # Main page
│   └── 📄 globals.css       # Global styles
│
├── 📁 components/           # React components
│   ├── 📁 simulation/       # Simulation-specific components
│   │   ├── 📄 ControlPanel.jsx      # Simulation controls
│   │   ├── 📄 MetricsPanel.jsx      # Performance metrics
│   │   ├── 📄 SimulationCanvas.jsx  # Visual simulation
│   │   └── 📄 *.jsx                 # Other simulation components
│   └── 📁 ui/              # Reusable UI components
│
├── 📁 hooks/               # Custom React hooks
│   ├── 📄 use-simulation-state.js  # State management
│   ├── 📄 use-simulation.js        # Simulation logic
│   └── 📄 *.js                     # Other hooks
│
└── 📁 lib/                 # Utility libraries
    ├── 📄 simulation-logic.js      # Core simulation algorithms
    ├── 📄 canvas-drawing.js        # Canvas rendering
    ├── 📄 node-management.js       # Node operations
    ├── 📄 placement-algorithms.js  # Placement strategies
    ├── 📄 event-handlers.js        # Event processing
    └── 📄 *.js                     # Other utilities
```

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
- **COLD_START**: `docker create` - Container created but not started
- **RUNNING**: `docker start` - Container actively executing requests
- **IDLE**: `docker stop` - Container stopped but available for reuse  
- **DEAD**: `docker rm` - Container removed from system

### 🔧 Advanced Features
- **Energy Monitoring**: Real-time energy consumption calculations
- **Network Simulation**: Latency and bandwidth modeling
- **User Mobility**: Dynamic user movement and service migration
- **Performance Analytics**: Comprehensive metrics collection and analysis

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core runtime environment
- **Flask**: RESTful API framework with CORS support
- **Docker API**: Container orchestration and management
- **TensorFlow/Scikit-learn**: Machine learning for prediction
- **Pandas/NumPy**: Data processing and analytics
- **Psutil**: System metrics collection

### Frontend  
- **Next.js 14**: React-based web framework
- **React 18**: Component-based UI development
- **Tailwind CSS**: Utility-first styling
- **Radix UI**: Accessible component library
- **Lucide React**: Icon library
- **Axios**: HTTP client for API communication

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
python central_main.py
# Or use deployment script:
./deploy_central.sh
```

### 5. Deploy Edge Nodes
```bash
# On each edge machine:
python edge_main.py --node-id edge_001 --central-url http://CENTRAL_IP:5001
# Or use deployment script:
./deploy_edge.sh
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
1. **Simulation Control**: Start/stop/reset simulation
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

### Load Testing
```bash
# Generate test workload
python -c "
import requests
for i in range(100):
    requests.post('http://localhost:5001/api/v1/central/execute', 
                  json={'function': 'test', 'payload': f'request_{i}'})
"
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

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Standards
- Python: Follow PEP 8 style guidelines
- JavaScript: Use ESLint and Prettier
- Documentation: Update README for new features
- Testing: Add unit tests for new functionality

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors & Acknowledgments

- **Core Development Team**: [Your Team Information]
- **Research Institution**: [Your Institution]
- **Funding**: [Grant/Funding Information if applicable]

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/truongng201/Serverless-edge-computing-simulation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/truongng201/Serverless-edge-computing-simulation/discussions)
- **Email**: [Your Contact Email]

## 🔮 Roadmap

### Upcoming Features
- [ ] Kubernetes integration
- [ ] Multi-cloud support  
- [ ] Advanced ML models (Transformer-based prediction)
- [ ] GraphQL API
- [ ] Real-time collaboration features
- [ ] Performance benchmarking suite
- [ ] Mobile device simulation

### Known Issues
- Container migration may fail under high network latency
- Web UI performance degrades with >50 concurrent nodes
- Memory leaks in long-running simulations (>24 hours)

---

**📚 For detailed deployment instructions, see [DEPLOYMENT.md](serverless-sim/DEPLOYMENT.md)**

**🔧 For backend architecture details, see [serverless-sim/README.md](serverless-sim/README.md)**