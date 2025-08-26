import { create } from 'zustand';

const useSimulationStore = create((set) => ({
  // Canvas ref
  canvasRef: { current: null },
  setCanvasRef: (ref) => set({ canvasRef: ref }),

  // Core simulation data
  users: [],
  edgeNodes: [],
  centralNodes: [],
  setUsers: (users) => set({ users }),
  setEdgeNodes: (edgeNodes) => set({ edgeNodes }),
  setCentralNodes: (centralNodes) => set({ centralNodes }),

  // Simulation state
  isSimulating: false,
  simulationSpeed: [1],
  predictionEnabled: true,
  totalLatency: 0,
  isDragging: false,
  setIsSimulating: (isSimulating) => set({ isSimulating }),
  setSimulationSpeed: (simulationSpeed) => set({ simulationSpeed }),
  setPredictionEnabled: (predictionEnabled) => set({ predictionEnabled }),
  setTotalLatency: (totalLatency) => set({ totalLatency }),
  setIsDragging: (isDragging) => set({ isDragging }),

  // UI State
  leftPanelOpen: false,
  rightPanelOpen: false,
  selectedModel: "lstm",
  selectedUser: null,
  selectedEdge: null,
  selectedCentral: null,
  setLeftPanelOpen: (leftPanelOpen) => set({ leftPanelOpen }),
  setRightPanelOpen: (rightPanelOpen) => set({ rightPanelOpen }),
  setSelectedModel: (selectedModel) => set({ selectedModel }),
  setSelectedUser: (selectedUser) => set({ selectedUser }),
  setSelectedEdge: (selectedEdge) => set({ selectedEdge }),
  setSelectedCentral: (selectedCentral) => set({ selectedCentral }),

  // User settings
  userSpeed: [5],
  userSize: [10],
  predictionSteps: [10],
  setUserSpeed: (userSpeed) => set({ userSpeed }),
  setUserSize: (userSize) => set({ userSize }),
  setPredictionSteps: (predictionSteps) => set({ predictionSteps }),

  // Node settings
  edgeCoverage: [500],
  centralCoverage: [0],
  setEdgeCoverage: (edgeCoverage) => set({ edgeCoverage }),
  setCentralCoverage: (centralCoverage) => set({ centralCoverage }),

  // Zoom and Pan state
  zoomLevel: 1,
  panOffset: { x: 0, y: 0 },
  isPanning: false,
  lastPanPoint: { x: 0, y: 0 },
  setZoomLevel: (zoomLevel) => set({ zoomLevel }),
  setPanOffset: (updater) =>
    set((state) => ({
      panOffset: typeof updater === "function"
        ? updater(state.panOffset)  
        : updater                    
    })),
  setIsPanning: (isPanning) => set({ isPanning }),
  setLastPanPoint: (lastPanPoint) => set({ lastPanPoint }),

  // Edit mode states
  editMode: "none",
  isDraggingNode: false,
  isDraggingUser: false,
  draggedNode: null,
  draggedUser: null,
  dragOffset: { x: 0, y: 0 },
  setEditMode: (editMode) => set({ editMode }),
  setIsDraggingNode: (isDraggingNode) => set({ isDraggingNode }),
  setIsDraggingUser: (isDraggingUser) => set({ isDraggingUser }),
  setDraggedNode: (draggedNode) => set({ draggedNode }),
  setDraggedUser: (draggedUser) => set({ draggedUser }),
  setDragOffset: (dragOffset) => set({ dragOffset }),

  // Manual connection state
  manualConnectionMode: false,
  autoAssignment: true,
  setManualConnectionMode: (manualConnectionMode) => set({ manualConnectionMode }),
  setAutoAssignment: (autoAssignment) => set({ autoAssignment }),

  // Live data state
  liveData: null,
  setLiveData: (liveData) => set({ liveData }),

  // Auto Placement state
  placementAlgorithm: "topk-demand",
  maxCoverageDistance: [100],
  setPlacementAlgorithm: (placementAlgorithm) => set({ placementAlgorithm }),
  setMaxCoverageDistance: (maxCoverageDistance) => set({ maxCoverageDistance }),

  // User Assignment state
  assignmentAlgorithm: "nearest-distance",
  setAssignmentAlgorithm: (assignmentAlgorithm) => set({ assignmentAlgorithm }),

  // Road Network state
  roadNetwork: null,
  setRoadNetwork: (roadNetwork) => set({ roadNetwork }),
  showRoads: false,
  setShowRoads: (showRoads) => set({ showRoads }),
  roads: [],
  setRoads: (roads) => set({ roads }),
  roadMode: false,
  setRoadMode: (roadMode) => set({ roadMode }),

  // Scenario selection state
  selectedScenario: "none",
  setSelectedScenario: (selectedScenario) => set({ selectedScenario }),

  // Simulation data
  simulationData: null,
  setSimulationData: (simulationData) => set({ simulationData }),

  // Real mode data
  realModeData: null,
  setRealModeData: (realModeData) => set({ realModeData }),


}));

export default useSimulationStore;
