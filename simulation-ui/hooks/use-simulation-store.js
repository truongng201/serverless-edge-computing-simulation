import { create } from 'zustand';

const useSimulationStore = create((set) => ({
  // Canvas ref
  canvasRef: { current: null },
  setCanvasRef: (ref) => set({ canvasRef: ref }),

  // Core simulation data
  users: [],
  edgeNodes: [],
  centralNodes: [],
  setUsers: (updater) =>
    set((state) => ({
      users: typeof updater === "function"
        ? updater(state.users)
        : updater
    })),
  setEdgeNodes: (updater) =>
    set((state) => ({
      edgeNodes: typeof updater === "function"
        ? updater(state.edgeNodes)
        : updater
    })),
  setCentralNodes: (updater) =>
    set((state) => ({
      centralNodes: typeof updater === "function"
        ? updater(state.centralNodes)
        : updater
    })),

  // Simulation state
  isSimulating: false,
  simulationSpeed: [1],
  predictionEnabled: true,
  totalLatency: 0,
  isDragging: false,
  setIsSimulating: (updater) =>
    set((state) => ({
      isSimulating: typeof updater === "function"
        ? updater(state.isSimulating)
        : updater
    })),
  setSimulationSpeed: (updater) =>
    set((state) => ({
      simulationSpeed: typeof updater === "function"
        ? updater(state.simulationSpeed)
        : updater
    })),
  setPredictionEnabled: (updater) =>
    set((state) => ({
      predictionEnabled: typeof updater === "function"
        ? updater(state.predictionEnabled)
        : updater
    })),
  setTotalLatency: (updater) =>
    set((state) => ({
      totalLatency: typeof updater === "function"
        ? updater(state.totalLatency)
        : updater
    })),
  setIsDragging: (updater) =>
    set((state) => ({
      isDragging: typeof updater === "function"
        ? updater(state.isDragging)
        : updater
    })),

  // UI State
  leftPanelOpen: false,
  rightPanelOpen: false,
  models: {
    lstm: "Long Short-Term Memory (LSTM)",
    cnn: "Convolutional Neural Network (CNN)",
    rnn: "Recurrent Neural Network (RNN)",
  },
  selectedModel: "lstm",
  selectedUser: null,
  selectedEdge: null,
  selectedCentral: null,
  setLeftPanelOpen: (updater) =>
    set((state) => ({
      leftPanelOpen: typeof updater === "function"
        ? updater(state.leftPanelOpen)
        : updater
    })),
  setRightPanelOpen: (updater) =>
    set((state) => ({
      rightPanelOpen: typeof updater === "function"
        ? updater(state.rightPanelOpen)
        : updater
    })),
  setSelectedModel: (updater) =>
    set((state) => ({
      selectedModel: typeof updater === "function"
        ? updater(state.selectedModel)
        : updater
    })),
  setSelectedUser: (updater) =>
    set((state) => ({
      selectedUser: typeof updater === "function"
        ? updater(state.selectedUser)
        : updater
    })),
  setSelectedEdge: (updater) =>
    set((state) => ({
      selectedEdge: typeof updater === "function"
        ? updater(state.selectedEdge)
        : updater
    })),
  setSelectedCentral: (updater) =>
    set((state) => ({
      selectedCentral: typeof updater === "function"
        ? updater(state.selectedCentral)
        : updater
    })),

  // User settings
  userSpeed: [5],
  userSize: [10],
  predictionSteps: [10],
  setUserSpeed: (updater) =>
    set((state) => ({
      userSpeed: typeof updater === "function"
        ? updater(state.userSpeed)
        : updater
    })),
  setUserSize: (updater) =>
    set((state) => ({
      userSize: typeof updater === "function"
        ? updater(state.userSize)
        : updater
    })),
  setPredictionSteps: (updater) =>
    set((state) => ({
      predictionSteps: typeof updater === "function"
        ? updater(state.predictionSteps)
        : updater
    })),

  // Node settings
  edgeCoverage: [500],
  centralCoverage: [0],
  setEdgeCoverage: (updater) =>
    set((state) => ({
      edgeCoverage: typeof updater === "function"
        ? updater(state.edgeCoverage)
        : updater
    })),
  setCentralCoverage: (updater) =>
    set((state) => ({
      centralCoverage: typeof updater === "function"
        ? updater(state.centralCoverage)
        : updater
    })),

  // Zoom and Pan state
  zoomLevel: 1,
  panOffset: { x: 0, y: 0 },
  isPanning: false,
  lastPanPoint: { x: 0, y: 0 },
  setZoomLevel: (updater) =>
    set((state) => ({
      zoomLevel: typeof updater === "function"
        ? updater(state.zoomLevel) 
        : updater,                   
    })),
  setPanOffset: (updater) =>
    set((state) => ({
      panOffset: typeof updater === "function"
        ? updater(state.panOffset)  
        : updater                    
    })),
  setIsPanning: (isPanning) => set({ isPanning }),
  setLastPanPoint: (updater) =>
    set((state) => ({
      lastPanPoint: typeof updater === "function"
        ? updater(state.lastPanPoint)
        : updater
    })),

  // Edit mode states
  editMode: "none",
  isDraggingNode: false,
  isDraggingUser: false,
  draggedNode: null,
  draggedUser: null,
  dragOffset: { x: 0, y: 0 },
  setEditMode: (updater) =>
    set((state) => ({
      editMode: typeof updater === "function"
        ? updater(state.editMode)
        : updater
    })),
  setIsDraggingNode: (updater) =>
    set((state) => ({
      isDraggingNode: typeof updater === "function"
        ? updater(state.isDraggingNode)
        : updater
    })),
  setIsDraggingUser: (updater) =>
    set((state) => ({
      isDraggingUser: typeof updater === "function"
        ? updater(state.isDraggingUser)
        : updater
    })),
  setDraggedNode: (updater) =>
    set((state) => ({
      draggedNode: typeof updater === "function"
        ? updater(state.draggedNode)
        : updater
    })),
  setDraggedUser: (updater) =>
    set((state) => ({
      draggedUser: typeof updater === "function"
        ? updater(state.draggedUser)
        : updater
    })),
  setDragOffset: (updater) =>
    set((state) => ({
      dragOffset: typeof updater === "function"
        ? updater(state.dragOffset)
        : updater
    })),

  // Live data state
  liveData: null,
  setLiveData: (updater) =>
    set((state) => ({
      liveData: typeof updater === "function"
        ? updater(state.liveData)
        : updater
    })),

  // Auto Placement state
  placementAlgorithm: "topk-demand",
  setPlacementAlgorithm: (updater) =>
    set((state) => ({
      placementAlgorithm: typeof updater === "function"
        ? updater(state.placementAlgorithm)
        : updater
    })),
  
  // User Assignment state
  assignmentAlgorithm: "nearest-distance",
  setAssignmentAlgorithm: (updater) =>
    set((state) => ({
      assignmentAlgorithm: typeof updater === "function"
        ? updater(state.assignmentAlgorithm)
        : updater
    })),

  // Road Network state
  roadNetwork: null,
  setRoadNetwork: (updater) =>
    set((state) => ({
      roadNetwork: typeof updater === "function"
        ? updater(state.roadNetwork)
        : updater
    })),
  showRoads: false,
  setShowRoads: (updater) =>
    set((state) => ({
      showRoads: typeof updater === "function"
        ? updater(state.showRoads)
        : updater
    })),
  roads: [],
  setRoads: (updater) =>
    set((state) => ({
      roads: typeof updater === "function"
        ? updater(state.roads)
        : updater
    })),
  roadMode: false,
  setRoadMode: (updater) =>
    set((state) => ({
      roadMode: typeof updater === "function"
        ? updater(state.roadMode)
        : updater
    })),

  // Scenario selection state
  selectedScenario: "none",
  setSelectedScenario: (updater) =>
    set((state) => ({
      selectedScenario: typeof updater === "function"
        ? updater(state.selectedScenario)
        : updater
    })),

  // Simulation data
  simulationData: null,
  setSimulationData: (updater) =>
    set((state) => ({
      simulationData: typeof updater === "function"
        ? updater(state.simulationData)
        : updater
    })),

  // Real mode data
  realModeData: null,
  setRealModeData: (updater) =>
    set((state) => ({
      realModeData: typeof updater === "function"
        ? updater(state.realModeData)
        : updater
    })),


}));

export default useSimulationStore;
