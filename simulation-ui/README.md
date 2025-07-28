# Digital Twin Simulation with Hierarchical Serverless Functions

## Description

This repository contains an **interactive digital twin simulation** that demonstrates hierarchical edge computing with predictive replica placement. The simulation models a network of cloudlets (edge nodes) and cloud servers, implementing advanced latency calculation based on experimental formulas for research purposes.

## Features

- **Real-time Interactive Simulation**: Canvas-based visualization with 10 FPS animation
- **5 Prediction Algorithms**: Linear, Kalman Filter, Markov Chain, Neural Network, Gravity Model
- **Advanced Latency Modeling**: Experimental formulas for communication and processing delays
- **Hierarchical Architecture**: Edge nodes (cloudlets) and central nodes (cloud servers)
- **Cold/Warm Start Simulation**: Container state management with timeout
- **Comprehensive UI**: Drag & drop, zoom/pan, real-time metrics
- **Research Tools**: Detailed latency breakdown and performance analytics

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
│   ├── components.js                 # Component utilities
│   └── helper.js                     # Helper functions
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
- **Core State Management**: Users, edge nodes, central nodes
- **Prediction Algorithms**: 5 different mobility prediction methods
- **Latency Calculation**: Experimental formula implementation
- **Canvas Rendering**: Real-time visualization with zoom/pan
- **Physics Simulation**: User movement with collision detection
- **Container Management**: Warm/cold start simulation

### **Control Panel (`ControlPanelContent.jsx`)**
- **Edit Modes**: None, nodes, users, both
- **Connection Management**: Manual/auto assignment
- **Node Controls**: Add/remove, capacity, coverage settings
- **User Settings**: Speed, size, prediction parameters
- **Simulation Controls**: Play/pause, speed, algorithm selection
- **Clear Functions**: Reset various simulation components

### **Metrics Panel (`MetricsPanelContent.jsx`)**
- **System Status**: User count, node status, average latency
- **Connection Monitoring**: Real-time connection status
- **Node Performance**: Load monitoring with warm/cold indicators
- **Latency Breakdown**: Detailed experimental formula metrics
- **Algorithm Information**: Current prediction method details

### **UI Components (`components/ui/`)**
- **shadcn/ui Library**: Consistent, accessible component system
- **Variant Support**: Multiple styles and sizes
- **Tailwind Integration**: Utility-first styling approach

## Latency Modeling

The simulation implements experimental latency formulas:

### **Total Service Delay**
```
D(u,v,t) = d_com(u,v,t) + d_proc(u,v,t)
```

### **Communication Delay**
```
d_com(u,v,t) = s(u,t) × τ(v_u,t, v)
```
- **Data Size**: [100, 500] MB
- **Transmission Rate**: Edge [0.2, 1] ms/MB, Cloud [2, 10] ms/MB

### **Processing Delay**
```
d_proc(u,v,t) = (1 - I_u,v,t) × d_cold + s(u,t) × ρ_u,v
```
- **Cold Start Penalty**: [100, 500] ms
- **Processing Rate**: Edge [0.5, 2] ms/MB, Cloud [0.05] ms/MB
- **Container Timeout**: 30 seconds inactivity

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

## Interaction Guide

### **Basic Operations:**
- **Click Canvas**: Add new users
- **Click Objects**: Select users/nodes
- **Mouse Wheel**: Zoom in/out
- **Ctrl + Drag**: Pan canvas

### **Edit Modes:**
- **None**: Default user creation mode
- **Nodes**: Drag nodes to reposition
- **Users**: Drag users to move
- **Both**: Edit all objects

### **Advanced Features:**
- **Manual Connections**: Select user → Choose node from dropdown
- **Algorithm Testing**: Switch between 5 prediction methods
- **Performance Monitoring**: Real-time latency and load metrics
- **Container Simulation**: Observe warm/cold start behavior

## Research Applications

This simulation is designed for:
- **Edge Computing Research**: Performance comparison studies
- **Latency Optimization**: Algorithm validation
- **Container Management**: Cold start impact analysis
- **Load Balancing**: Distribution strategy testing
- **Mobility Prediction**: Algorithm effectiveness evaluation

## Technology Stack

- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS + shadcn/ui
- **Visualization**: HTML5 Canvas
- **State Management**: React hooks
- **Icons**: Lucide React
- **Build Tools**: PostCSS, ESLint
