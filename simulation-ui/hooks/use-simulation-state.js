import { useState, useRef, useEffect } from "react";
import { useSimulation } from "@/hooks/use-simulation";

export function useSimulationState() {
  const canvasRef = useRef(null);
  const [users, setUsers] = useState([]);
  const [edgeNodes, setEdgeNodes] = useState([]);
  const [centralNodes, setCentralNodes] = useState([]);

  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState([1]);
  const [predictionEnabled, setPredictionEnabled] = useState(true);
  const [totalLatency, setTotalLatency] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // UI State
  const [leftPanelOpen, setLeftPanelOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState("lstm");
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);

  // User settings
  const [userSpeed, setUserSpeed] = useState([2]);
  const [userSize, setUserSize] = useState([8]);
  const [predictionSteps, setPredictionSteps] = useState([10]);

  // Edge settings
  const [edgeCapacity, setEdgeCapacity] = useState([100]);
  const [edgeCoverage, setEdgeCoverage] = useState([80]);

  // Central node settings
  const [centralCapacity, setCentralCapacity] = useState([500]);
  const [centralCoverage, setCentralCoverage] = useState([150]);

  // Zoom and Pan state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 });

  // Edit mode states
  const [editMode, setEditMode] = useState("none"); // "none", "nodes", "users", "both"
  const [isDraggingNode, setIsDraggingNode] = useState(false);
  const [isDraggingUser, setIsDraggingUser] = useState(false);
  const [draggedNode, setDraggedNode] = useState(null);
  const [draggedUser, setDraggedUser] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Manual connection state
  const [manualConnectionMode, setManualConnectionMode] = useState(false);
  const [autoAssignment, setAutoAssignment] = useState(true);

  // Simulation mode state
  const [simulationMode, setSimulationMode] = useState("demo"); // "demo" or "real"
  const [realModeData, setRealModeData] = useState(null);

  // Auto Placement state
  const [placementAlgorithm, setPlacementAlgorithm] = useState("topk-demand");
  const [maxCoverageDistance, setMaxCoverageDistance] = useState([100]);

  // Simulation data management using REST API
  // Disabled to prevent conflicts with ControlPanelContent direct API calls
  // const simulationData = useSimulation('http://localhost:5001', isSimulating, simulationSpeed[0], setUsers);
  const simulationData = null; // Temporarily disabled

  // Update coverage for existing nodes when slider changes
  useEffect(() => {
    setEdgeNodes(prev => prev.map(edge => ({
      ...edge,
      coverage: edgeCoverage[0]
    })));
  }, [edgeCoverage]);

  useEffect(() => {
    setCentralNodes(prev => prev.map(central => ({
      ...central,
      coverage: centralCoverage[0]
    })));
  }, [centralCoverage]);

  // Container timeout management - reset warm state after 30 seconds of inactivity
  useEffect(() => {
    const interval = setInterval(() => {
      const currentTime = Date.now();
      const timeoutDuration = 30000; // 30 seconds

      // Reset warm state for edge nodes
      setEdgeNodes(prev => prev.map(edge => {
        if (edge.isWarm && edge.lastAccessTime && 
            (currentTime - edge.lastAccessTime) > timeoutDuration) {
          return { ...edge, isWarm: false, lastAccessTime: null };
        }
        return edge;
      }));

      // Reset warm state for central nodes
      setCentralNodes(prev => prev.map(central => {
        if (central.isWarm && central.lastAccessTime && 
            (currentTime - central.lastAccessTime) > timeoutDuration) {
          return { ...central, isWarm: false, lastAccessTime: null };
        }
        return central;
      }));
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return {
    canvasRef,
    users,
    setUsers,
    edgeNodes,
    setEdgeNodes,
    centralNodes,
    setCentralNodes,
    isSimulating,
    setIsSimulating,
    simulationSpeed,
    setSimulationSpeed,
    predictionEnabled,
    setPredictionEnabled,
    totalLatency,
    setTotalLatency,
    isDragging,
    setIsDragging,
    leftPanelOpen,
    setLeftPanelOpen,
    rightPanelOpen,
    setRightPanelOpen,
    selectedModel,
    setSelectedModel,
    selectedUser,
    setSelectedUser,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
    userSpeed,
    setUserSpeed,
    userSize,
    setUserSize,
    predictionSteps,
    setPredictionSteps,
    edgeCapacity,
    setEdgeCapacity,
    edgeCoverage,
    setEdgeCoverage,
    centralCapacity,
    setCentralCapacity,
    centralCoverage,
    setCentralCoverage,
    zoomLevel,
    setZoomLevel,
    panOffset,
    setPanOffset,
    isPanning,
    setIsPanning,
    lastPanPoint,
    setLastPanPoint,
    editMode,
    setEditMode,
    isDraggingNode,
    setIsDraggingNode,
    isDraggingUser,
    setIsDraggingUser,
    draggedNode,
    setDraggedNode,
    draggedUser,
    setDraggedUser,
    dragOffset,
    setDragOffset,
    manualConnectionMode,
    setManualConnectionMode,
    autoAssignment,
    setAutoAssignment,
    simulationMode,
    setSimulationMode,
    realModeData,
    setRealModeData,
    placementAlgorithm,
    setPlacementAlgorithm,
    maxCoverageDistance,
    setMaxCoverageDistance,
  };
}
