# Digital Twin Simulation with Hierarchical Serverless Functions

## Description

This repository contains an **interactive digital twin simulation** that demonstrates hierarchical edge computing with predictive replica placement. The simulation models a network of cloudlets (edge nodes) and cloud servers, implementing advanced latency calculation based on experimental formulas for research purposes.

## Features

- **Real-time Interactive Simulation**: Canvas-based visualization with 10 FPS animation
- **Multiple Simulation Scenarios**: Manual, DACT Dataset, Vehicle Data, and Street Map scenarios
- **Realistic Street Map Simulation**: Saigon-inspired road network with traffic lights and pathfinding
- **Serverless Function Simulation**: Complete serverless workload modeling with function types
- **GAP-based Assignment Algorithms**: Nearest Distance, Load Aware, Resource Aware, and GAP Baseline
- **Advanced Latency Modeling**: Experimental formulas with communication, processing, and cold-start delays
- **Hierarchical Architecture**: Edge nodes (cloudlets) and central nodes (cloud servers)
- **Traffic Management System**: Coordinated traffic lights with realistic vehicle movement
- **Backend Integration**: Full API integration with central node for user lifecycle management
- **Comprehensive UI**: Drag & drop, zoom/pan, real-time metrics with detailed analytics
- **Research Tools**: Performance comparison, latency breakdown, and assignment algorithm analysis

## Project Structure

```
hierarchical-digital-twin/
├── app/                              # Next.js App Router
│   ├── page.jsx                      # Main page entry point
│   ├── layout.jsx                    # Root layout with metadata
│   └── globals.css                   # Global CSS styles
├── components/                       # React components
│   ├── simulation/                   # Simulation-specific components
│   │   ├── ControlPanel.jsx          # Left panel wrapper
│   │   ├── ControlPanelContent.jsx   # Control panel functionality
│   │   ├── MetricsPanel.jsx          # Right panel wrapper
│   │   ├── MetricsPanelContent.jsx   # Metrics and monitoring
│   │   ├── SimulationCanvas.jsx      # Canvas component
│   │   └── EditModeDescription.jsx   # Instructions display
│   ├── ui/                           # Reusable UI components (shadcn/ui)
│   │   ├── button.jsx                # Button component
│   │   ├── card.jsx                  # Card layout component
│   │   ├── input.jsx                 # Input field component
│   │   ├── label.jsx                 # Label component
│   │   ├── progress.jsx              # Progress bar component
│   │   ├── select.jsx                # Dropdown select component
│   │   ├── slider.jsx                # Range slider component
│   │   ├── switch.jsx                # Toggle switch component
│   │   └── badge.jsx                 # Status badge component
│   └── theme-provider.jsx            # Theme context provider
├── hooks/                            # Custom React hooks
│   ├── use-mobile.js                 # Mobile device detection
│   └── use-toast.js                  # Toast notification system
├── lib/                              # Utility libraries
│   ├── utils.js                      # Utility functions (clsx, tw-merge)
│   ├── helper.js                     # Helper functions
│   ├── simulation-logic.js           # Core simulation step logic
│   ├── canvas-drawing.js             # Canvas rendering and visualization
│   ├── event-handlers.js             # Mouse and keyboard event handling
│   ├── node-management.js            # Edge/central node management
│   ├── user-management.js            # User lifecycle and movement
│   ├── placement-algorithms.js       # GAP and other placement algorithms
│   ├── gap-solver.js                 # GAP optimization solver
│   ├── road-network.js               # Street map and traffic light system
│   └── street-map-users.js           # Vehicle management and serverless integration
├── public/                           # Static assets
│   └── placeholder.svg               # Placeholder graphics
├── digital-twin-simulation.jsx       # Main simulation component
├── package.json                      # Node.js dependencies
├── next.config.mjs                   # Next.js configuration
├── tailwind.config.js                # Tailwind CSS configuration
├── postcss.config.js                 # PostCSS configuration
├── jsconfig.json                     # JavaScript configuration
└── README.md                         # Project documentation
```

## Core Components

### **Main Simulation (`digital-twin-simulation.jsx`)**
- **Core State Management**: Users, edge nodes, central nodes, road networks
- **Scenario Management**: Multiple simulation modes with data loading
- **Assignment Algorithms**: GAP-based optimization with multiple strategies
- **Canvas Rendering**: Real-time visualization with zoom/pan and street map rendering
- **Physics Simulation**: Vehicle movement with traffic light integration
- **Container Management**: Warm/cold start simulation with serverless functions

### **Control Panel (`ControlPanelContent.jsx`)**
- **Scenario Selection**: Manual, DACT Dataset, Vehicle Data, Street Map modes
- **Assignment Algorithms**: Nearest Distance, Load Aware, Resource Aware, GAP Baseline
- **GAP Solver Integration**: Automated edge server placement optimization
- **Node Controls**: Add/remove, capacity, coverage, manual positioning
- **User Settings**: Speed, size, spawn rate, traffic parameters
- **Simulation Controls**: Play/pause, speed, real-time data polling
- **Clear Functions**: Reset simulation with backend synchronization

### **Metrics Panel (`MetricsPanelContent.jsx`)**
- **System Status**: User count, node status, average latency, assignment distribution
- **Street Map Metrics**: Vehicle count, traffic lights, function execution statistics
- **Assignment Performance**: Algorithm comparison and efficiency metrics
- **Node Performance**: Load monitoring with warm/cold container indicators
- **Latency Breakdown**: Communication, processing, and cold-start delay analysis
- **Serverless Analytics**: Function types, execution frequency, resource utilization

### **UI Components (`components/ui/`)**
- **shadcn/ui Library**: Consistent, accessible component system
- **Variant Support**: Multiple styles and sizes
- **Tailwind Integration**: Utility-first styling approach

## Simulation Scenarios

### **Scenario 1: Manual Mode**
- **Interactive User Placement**: Click to add users anywhere on canvas
- **Manual Node Assignment**: Select users and assign to specific edge/central nodes
- **Real-time Editing**: Drag nodes and users to test different configurations

### **Scenario 2: DACT Dataset**
- **Research Data Integration**: Load pre-defined user distributions from DACT dataset
- **Consistent Testing**: Reproducible scenarios for algorithm comparison
- **Academic Validation**: Use established datasets for research validation

### **Scenario 3: Vehicle Data**
- **Mobility Patterns**: Load vehicle movement data for realistic user behavior
- **Temporal Analysis**: Time-based user distribution and movement patterns
- **Transportation Research**: Study edge computing in vehicular networks

### **Scenario 4: Street Map (Saigon)**
- **Realistic Road Network**: Grid-based street layout inspired by Saigon
- **Traffic Light System**: Coordinated traffic lights with 5-second cycles and phase offsets
- **Vehicle Simulation**: Autonomous vehicles with pathfinding and traffic rule compliance
- **Serverless Integration**: Vehicles act as serverless users with function execution
- **Auto Spawn/Despawn**: Dynamic user lifecycle with destination-based removal

## Assignment Algorithms

### **Nearest Distance**
- **Geographic Optimization**: Assign users to closest available node
- **Low Latency Focus**: Minimize communication delay through proximity
- **Simple Strategy**: Baseline algorithm for comparison

### **Load Aware**
- **Resource Balancing**: Consider current node load and capacity
- **Performance Optimization**: Prevent node overload and bottlenecks
- **Dynamic Adjustment**: Real-time load monitoring and redistribution

### **Resource Aware**
- **Function-Specific Assignment**: Match user requirements with node capabilities
- **CPU/Memory Optimization**: Consider processing power and memory requirements
- **Workload Matching**: Assign based on function type and resource needs

### **GAP Baseline**
- **Optimization Algorithm**: Generalized Assignment Problem solver
- **Multi-objective**: Balance latency, load, and resource constraints
- **Research Grade**: Advanced algorithm for academic comparison

## Latency Modeling

### **Total Service Delay**
```
D(u,v,t) = d_com(u,v,t) + d_proc(u,v,t)
```

### **Communication Delay**
```
d_com(u,v,t) = s(u,t) × τ(v_u,t, v) + propagation_delay
```
- **Data Size**: [1-50] MB (configurable by function type)
- **Transmission Rate**: Edge [0.5-2] ms/MB, Cloud [2-10] ms/MB
- **Propagation Delay**: Distance-based with speed of light calculation

### **Processing Delay**
```
d_proc(u,v,t) = (1 - I_u,v,t) × d_cold + s(u,t) × ρ_u,v
```
- **Cold Start Penalty**: [100-500] ms (function type dependent)
- **Processing Rate**: Edge [0.5-2] ms/MB, Cloud [0.1-0.5] ms/MB
- **Container Timeout**: 30 seconds inactivity threshold

### **Serverless Function Types**
- **Web API**: Low CPU, medium memory, frequent requests
- **Data Processing**: High CPU, high memory, batch processing
- **IoT Handler**: Low resources, high frequency, small data
- **ML Inference**: High CPU, very high memory, variable load
- **File Storage**: Medium CPU, low memory, large data transfers

## Installation

### Requirements:
- **Node.js** (version 18 or higher)
- **npm** (Node package manager)

### Setup:
```bash
# Clone the repository
git clone <repository-url>

# Navigate to the project directory
cd hierarchical-digital-twin

# Install dependencies
npm install
```

## Usage

### **Development Mode:**
```bash
npm run dev
```

### **Production Build:**
```bash
npm run build
npm run start
```

### **Linting:**
```bash
npm run lint
```

Open your web browser and navigate to `http://localhost:3000` to view the simulation.

## Backend Integration

### **Environment Configuration:**
Create a `.env.local` file in the simulation-ui directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### **Required Backend APIs:**
The simulation requires a running central node with the following endpoints:
- `POST /api/v1/central/create_user_node` - Create users in backend
- `POST /api/v1/central/update_user_node` - Update user positions
- `DELETE /api/v1/central/delete_user/<user_id>` - Remove specific users
- `DELETE /api/v1/central/delete_all_users` - Clear all users
- `GET /api/v1/central/cluster/status` - Get node status and metrics

### **Backend Setup:**
Refer to the `serverless-sim/` directory for central node setup instructions.

## Interaction Guide

### **Basic Operations:**
- **Click Canvas**: Add new users (Manual mode)
- **Click Objects**: Select users/nodes for detailed information
- **Mouse Wheel**: Zoom in/out for different detail levels
- **Ctrl + Drag**: Pan canvas to explore large simulations

### **Scenario Management:**
- **Scenario Selection**: Choose from Manual, DACT, Vehicle, or Street Map modes
- **Data Loading**: Automatic data fetching and user population
- **Clear Functions**: Reset simulation and backend state

### **Edit Modes:**
- **None**: Default user creation and selection mode
- **Nodes**: Drag edge/central nodes to reposition
- **Users**: Drag individual users to test mobility
- **Both**: Edit all simulation objects

### **Assignment Controls:**
- **Algorithm Selection**: Switch between Nearest Distance, Load Aware, Resource Aware, GAP Baseline
- **Manual Assignment**: Select user → Choose specific node from dropdown
- **GAP Batch Assignment**: Run optimization algorithm on all users
- **Real-time Assignment**: Automatic assignment for new users

### **Street Map Features:**
- **Traffic Light Viewing**: Zoom in to see individual light states and directions
- **Vehicle Tracking**: Follow individual vehicles on their routes
- **Road Network**: Realistic two-way roads with lane markings
- **Spawning Control**: Adjust vehicle spawn rate and maximum count

### **Advanced Features:**
- **Backend Integration**: Real-time synchronization with central node API
- **Performance Monitoring**: Detailed latency, load, and assignment metrics
- **Function Simulation**: Observe serverless function execution and cold starts
- **Research Tools**: Algorithm comparison and performance analysis

## Research Applications

This simulation is designed for:
- **Edge Computing Research**: Multi-scenario performance comparison with real datasets
- **Assignment Algorithm Analysis**: GAP vs heuristic algorithm validation and benchmarking
- **Serverless Computing**: Function type modeling, cold start analysis, container management
- **Traffic Engineering**: Vehicle routing, traffic light optimization, urban mobility patterns
- **Latency Optimization**: Communication vs processing delay trade-offs in hierarchical systems
- **Load Balancing**: Dynamic resource allocation and distribution strategy testing
- **Urban Computing**: Smart city applications, IoT deployment, vehicular edge networks
- **Academic Validation**: Reproducible experiments with established datasets (DACT, Vehicle data)

## Technology Stack

### **Frontend**
- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS + shadcn/ui
- **Visualization**: HTML5 Canvas with zoom/pan support
- **State Management**: React hooks with custom simulation state
- **Icons**: Lucide React
- **Build Tools**: PostCSS, ESLint

### **Backend Integration**
- **API Communication**: RESTful APIs with central node
- **Data Management**: Real-time user lifecycle synchronization
- **Algorithm Integration**: GAP solver and assignment algorithms
- **Performance Monitoring**: Live metrics and analytics

### **Simulation Engine**
- **Road Network**: Custom pathfinding with Dijkstra algorithm
- **Traffic Management**: Coordinated traffic light system
- **Physics**: Vehicle movement with collision detection
- **Serverless Modeling**: Function type simulation with resource modeling
