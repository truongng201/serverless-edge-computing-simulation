import { create } from 'zustand';
import { calculateLatency } from '../lib/placement-algorithms';
import { calculateDistance } from '../lib/helper';

const useSimulationStore = create((set, get) => ({
  // Canvas ref
  canvasRef: null,
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
  setPanOffset: (panOffset) => set({ panOffset }),
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

  // Simulation mode
  simulationMode: "normal",
  setSimulationMode: (simulationMode) => set({ simulationMode }),

  // Real mode data
  realModeData: null,
  setRealModeData: (realModeData) => set({ realModeData }),

  // Actions
  updateTotalLatency: () => {
    const { users } = get();
    if (!users || users.length === 0) {
      set({ totalLatency: 0 });
      return;
    }
    const sum = users.reduce((acc, u) => acc + (Number(u.latency) || 0), 0);
    set({ totalLatency: Math.round(sum / users.length) });
  },

  // Auto-assignment logic
  performAutoAssignment: () => {
    const { users, edgeNodes, centralNodes, autoAssignment } = get();
    
    if (!autoAssignment) return;
    if ((edgeNodes?.length || 0) + (centralNodes?.length || 0) === 0) return;
    if (!users || users.length === 0) return;

    const updatedUsers = users.map((u) => {
      let bestLatency = Number.POSITIVE_INFINITY;
      let bestType = null;
      let bestId = null;

      // Evaluate all edges
      for (let i = 0; i < edgeNodes.length; i++) {
        const n = edgeNodes[i];
        const lat = calculateLatency(u, n.id, "edge", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
        if (lat < bestLatency) { 
          bestLatency = lat; 
          bestType = "edge"; 
          bestId = n.id; 
        }
      }

      // Evaluate all centrals
      for (let i = 0; i < centralNodes.length; i++) {
        const c = centralNodes[i];
        const lat = calculateLatency(u, c.id, "central", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
        if (lat < bestLatency) { 
          bestLatency = lat; 
          bestType = "central"; 
          bestId = c.id; 
        }
      }

      if (!bestType || !bestId || !isFinite(bestLatency)) return u;

      return {
        ...u,
        assignedEdge: bestType === "edge" ? bestId : null,
        assignedCentral: bestType === "central" ? bestId : null,
        latency: bestLatency,
      };
    });

    set({ users: updatedUsers });
  },

  // Container timeout management
  resetWarmContainers: () => {
    const { edgeNodes, centralNodes } = get();
    const currentTime = Date.now();
    const timeoutDuration = 30000; // 30 seconds

    // Reset warm state for edge nodes
    const updatedEdgeNodes = edgeNodes.map(edge => {
      if (edge.isWarm && edge.lastAccessTime && 
          (currentTime - edge.lastAccessTime) > timeoutDuration) {
        return { ...edge, isWarm: false, lastAccessTime: null };
      }
      return edge;
    });

    // Reset warm state for central nodes
    const updatedCentralNodes = centralNodes.map(central => {
      if (central.isWarm && central.lastAccessTime && 
          (currentTime - central.lastAccessTime) > timeoutDuration) {
        return { ...central, isWarm: false, lastAccessTime: null };
      }
      return central;
    });

    set({ 
      edgeNodes: updatedEdgeNodes, 
      centralNodes: updatedCentralNodes 
    });
  },
}));

export default useSimulationStore;
