"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { MapPin, Settings } from "lucide-react";
import ControlPanel from "@/components/simulation/ControlPanel";
import MetricsPanel from "@/components/simulation/MetricsPanel";
import SimulationCanvas from "@/components/simulation/SimulationCanvas";
import EditModeDescription from "@/components/simulation/EditModeDescription";
import ControlPanelContent from "@/components/simulation/ControlPanelContent";
import MetricsPanelContent from "@/components/simulation/MetricsPanelContent";
import { calculateDistance, findNearestNode, getAllNodes } from "@/lib/helper";
import { CentralNode, EdgeNode, UserNode } from "./lib/components";
import { useSocket } from "@/hooks/use-socket";

export default function Component() {
  const canvasRef = useRef(null);
  const [users, setUsers] = useState([]);
  const [edgeNodes, setEdgeNodes] = useState([]);

  // Central nodes - main servers/coordinators
  const [centralNodes, setCentralNodes] = useState([]);
  const [graph, setGraph] = useState(new Map()); // adjacency list for graph representation

  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState([1]);
  const [predictionEnabled, setPredictionEnabled] = useState(true);
  const [totalLatency, setTotalLatency] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // UI State
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("linear");
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);

  // User settings
  const [userSpeed, setUserSpeed] = useState([2]);
  const [userSize, setUserSize] = useState([8]);
  const [predictionSteps, setPredictionSteps] = useState([10]);

  // Edge settings
  const [edgeCapacity, setEdgeCapacity] = useState([100]);
  const [edgeCoverage, setEdgeCoverage] = useState([0]);

  // Central node settings
  const [centralCapacity, setCentralCapacity] = useState([500]);
  const [centralCoverage, setCentralCoverage] = useState([0]);

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

  // Socket.IO for real-time data communication
  const socketData = useSocket('http://localhost:5001');

  // Algorithms for user expectancy calculation
  const algorithms = {
    linear: "Linear Prediction",
    // kalman: "Kalman Filter",
    // markov: "Markov Chain",
    // neural: "Neural Network",
    // gravity: "Gravity Model",
  };

  // Calculate distance between two points
  const calculateDistance = (x1, y1, x2, y2) => {
    return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
  };

  // Find nearest edge node to a user
  const findNearestEdge = (user) => {
    if (edgeNodes.length === 0) return null;
    return edgeNodes.reduce((nearest, edge) => {
      const distanceToEdge = calculateDistance(user.x, user.y, edge.x, edge.y);
      const distanceToNearest = calculateDistance(
        user.x,
        user.y,
        nearest.x,
        nearest.y
      );
      return distanceToEdge < distanceToNearest ? edge : nearest;
    });
  };

  // Find nearest central node to a user
  const findNearestCentral = (user) => {
    if (centralNodes.length === 0) return null;
    return centralNodes.reduce((nearest, central) => {
      const distanceToCentral = calculateDistance(
        user.x,
        user.y,
        central.x,
        central.y
      );
      const distanceToNearest = nearest
        ? calculateDistance(user.x, user.y, nearest.x, nearest.y)
        : Number.POSITIVE_INFINITY;
      return distanceToCentral < distanceToNearest ? central : nearest;
    });
  };

  // Get all available nodes for connection
  const getAllNodes = () => {
    return [
      ...edgeNodes.map((node) => ({ ...node, type: "edge" })),
      ...centralNodes.map((node) => ({ ...node, type: "central" })),
    ];
  };

  // Calculate latency based on connection using experimental formula
  const calculateLatency = (user, nodeId, nodeType) => {
    let targetNode = null;
    if (nodeType === "edge") {
      targetNode = edgeNodes.find((edge) => edge.id === nodeId);
    } else if (nodeType === "central") {
      targetNode = centralNodes.find((central) => central.id === nodeId);
    }

    if (!targetNode) return 100 + Math.random() * 50;

    // Generate random data size s(u,t) in range [100, 500] MB
    const dataSize = 100 + Math.random() * 400; // MB
    
    // Determine if it's Cold Start or Warm Start
    const isWarmStart = targetNode.isWarm || false; // I_{u,v,t}
    const coldStartIndicator = isWarmStart ? 1 : 0;
    
    // Calculate Communication Delay: d_com = s(u,t) × τ(v_u,t, v)
    let unitTransmissionDelay; // τ (ms/MB)
    if (nodeType === "edge") {
      // Between APs: [0.2, 1] ms/MB
      unitTransmissionDelay = 0.2 + Math.random() * 0.8;
    } else {
      // To Cloud: [2, 10] ms/MB  
      unitTransmissionDelay = 2 + Math.random() * 8;
    }
    const communicationDelay = dataSize * unitTransmissionDelay;
    
    // Calculate Processing Delay: d_proc = (1 - I_{u,v,t}) × d_cold + s(u,t) × ρ_{u,v}
    
    // Cold start delay [100, 500] ms
    const coldStartDelay = 100 + Math.random() * 400;
    
    // Unit processing time ρ_{u,v} (ms/MB)
    let unitProcessingTime;
    if (nodeType === "edge") {
      // Cloudlet: [0.5, 2] ms/MB
      unitProcessingTime = 0.5 + Math.random() * 1.5;
    } else {
      // Cloud: 0.05 ms/MB
      unitProcessingTime = 0.05;
    }
    
    const processingDelay = (1 - coldStartIndicator) * coldStartDelay + dataSize * unitProcessingTime;
    
    // Total Service Delay: D(u,v,t) = d_com + d_proc
    const totalLatency = communicationDelay + processingDelay;
    
    // Mark node as warm for next requests (simulating container reuse)
    if (targetNode) {
      targetNode.isWarm = true;
      targetNode.lastAccessTime = Date.now();
    }
    
    // Store additional metrics for debugging/display
    if (targetNode) {
      targetNode.lastMetrics = {
        dataSize: Math.round(dataSize),
        communicationDelay: Math.round(communicationDelay),
        processingDelay: Math.round(processingDelay),
        isWarmStart: isWarmStart,
        unitTransmissionDelay: unitTransmissionDelay.toFixed(3),
        unitProcessingTime: unitProcessingTime.toFixed(3)
      };
    }
    
    return Math.round(totalLatency);
  };

  // Manually connect user to a specific node
  const connectUserToNode = (userId, nodeId, nodeType) => {
    const allNodes = getAllNodes(edgeNodes, centralNodes);
    setUsers((prevUsers) =>
      prevUsers.map((user) => {
        if (user.id === userId) {
          const latency = calculateLatency(user, nodeId, allNodes);
          return {
            ...user,
            assignedEdge: nodeType === "edge" ? nodeId : null,
            assignedCentral: nodeType === "central" ? nodeId : null,
            manualConnection: true,
            latency,
          };
        }
        return user;
      })
    );
  };

  // Disconnect user from all nodes
  const disconnectUser = (userId) => {
    setUsers((prevUsers) => {
      const newUsers = [];
      for (let i = 0; i < prevUsers.length; i++) {
        const user = prevUsers[i];
        if (user.id === userId) {
          newUsers.push({
            ...user,
            assignedEdge: null,
            assignedCentral: null,
            manualConnection: false,
            latency: 100 + Math.random() * 50,
          });
        } else {
          newUsers.push(user);
        }
      }
      return newUsers;
    });
  };

  // Reset all manual connections
  const resetAllConnections = () => {
    setUsers((prevUsers) => {
      const newUsers = [];
      for (let i = 0; i < prevUsers.length; i++) {
        newUsers.push({ ...prevUsers[i], manualConnection: false });
      }
      return newUsers;
    });
  };

  // Update selected user properties
  const updateSelectedUser = (updates) => {
    if (!selectedUser) return;
    setUsers((prevUsers) => {
      const newUsers = [];
      for (let i = 0; i < prevUsers.length; i++) {
        const user = prevUsers[i];
        if (user.id === selectedUser.id) {
          newUsers.push({ ...user, ...updates });
        } else {
          newUsers.push(user);
        }
      }
      return newUsers;
    });
    setSelectedUser((prev) => ({ ...prev, ...updates }));
  };

  // Delete selected user
  const deleteSelectedUser = () => {
    if (!selectedUser) return;
    setUsers((prevUsers) => {
      const newUsers = [];
      for (let i = 0; i < prevUsers.length; i++) {
        if (prevUsers[i].id !== selectedUser.id) {
          newUsers.push(prevUsers[i]);
        }
      }
      return newUsers;
    });
    setSelectedUser(null);
  };

  // Different prediction algorithms
  const predictUserMobility = (user) => {
    const predictions = [];
    let currentX = user.x;
    let currentY = user.y;

    switch (selectedAlgorithm) {
      case "linear":
        for (let i = 1; i <= predictionSteps[0]; i++) {
          currentX += user.vx * i * 2;
          currentY += user.vy * i * 2;
          currentX = Math.max(10, Math.min(window.innerWidth - 10, currentX));
          currentY = Math.max(10, Math.min(window.innerHeight - 10, currentY));
          predictions.push({ x: currentX, y: currentY });
        }
        break;

      case "kalman":
        const noise = 0.1;
        for (let i = 1; i <= predictionSteps[0]; i++) {
          currentX += user.vx * i * 2 + (Math.random() - 0.5) * noise * i;
          currentY += user.vy * i * 2 + (Math.random() - 0.5) * noise * i;
          currentX = Math.max(10, Math.min(window.innerWidth - 10, currentX));
          currentY = Math.max(10, Math.min(window.innerHeight - 10, currentY));
          predictions.push({ x: currentX, y: currentY });
        }
        break;

      case "markov":
        for (let i = 1; i <= predictionSteps[0]; i++) {
          const stateChange = Math.random();
          if (stateChange < 0.7) {
            currentX += user.vx * 2;
            currentY += user.vy * 2;
          } else {
            currentX += (Math.random() - 0.5) * 8;
            currentY += (Math.random() - 0.5) * 8;
          }
          currentX = Math.max(10, Math.min(window.innerWidth - 10, currentX));
          currentY = Math.max(10, Math.min(window.innerHeight - 10, currentY));
          predictions.push({ x: currentX, y: currentY });
        }
        break;

      case "neural":
        for (let i = 1; i <= predictionSteps[0]; i++) {
          const weight1 = 0.8,
            weight2 = 0.6,
            bias = 0.1;
          currentX += (user.vx * weight1 + user.vy * weight2 + bias) * 2;
          currentY += (user.vy * weight1 + user.vx * weight2 + bias) * 2;
          currentX = Math.max(10, Math.min(window.innerWidth - 10, currentX));
          currentY = Math.max(10, Math.min(window.innerHeight - 10, currentY));
          predictions.push({ x: currentX, y: currentY });
        }
        break;

      case "gravity":
        for (let i = 1; i <= predictionSteps[0]; i++) {
          let forceX = 0,
            forceY = 0;
          // Attraction to edge nodes
          edgeNodes.forEach((edge) => {
            const distance = calculateDistance(
              currentX,
              currentY,
              edge.x,
              edge.y
            );
            const force = 100 / (distance + 1);
            forceX += (edge.x - currentX) * force * 0.001;
            forceY += (edge.y - currentY) * force * 0.001;
          });
          // Stronger attraction to central nodes
          centralNodes.forEach((central) => {
            const distance = calculateDistance(
              currentX,
              currentY,
              central.x,
              central.y
            );
            const force = 200 / (distance + 1);
            forceX += (central.x - currentX) * force * 0.001;
            forceY += (central.y - currentY) * force * 0.001;
          });
          currentX += user.vx * 2 + forceX;
          currentY += user.vy * 2 + forceY;
          currentX = Math.max(10, Math.min(window.innerWidth - 10, currentX));
          currentY = Math.max(10, Math.min(window.innerHeight - 10, currentY));
          predictions.push({ x: currentX, y: currentY });
        }
        break;

      default:
        return predictions;
    }

    return predictions;
  };

  // Optimize replica placement based on predictions
  const optimizeReplicaPlacement = useCallback(() => {
    if (!predictionEnabled) return;

    const updatedUsers = users.map((user) => {
      const predictedPath = predictUserMobility(user);

      // Skip automatic assignment if user has manual connection
      if (user.manualConnection || !autoAssignment) {
        return {
          ...user,
          predictedPath,
        };
      }

      const nearestEdge = findNearestNode(edgeNodes, user);
      const nearestCentral = findNearestNode(centralNodes, user);

      // Calculate latency using experimental formula for both edge and central nodes
      let bestLatency = Number.POSITIVE_INFINITY;
      let assignedEdge = null;
      let assignedCentral = null;

      if (nearestEdge) {
        const edgeLatency = calculateLatency(user, nearestEdge.id, "edge");
        if (edgeLatency < bestLatency) {
          bestLatency = edgeLatency;
          assignedEdge = nearestEdge.id;
          assignedCentral = null;
        }
      }

      if (nearestCentral) {
        const centralLatency = calculateLatency(user, nearestCentral.id, "central");
        if (centralLatency < bestLatency) {
          bestLatency = centralLatency;
          assignedEdge = null;
          assignedCentral = nearestCentral.id;
        }
      }

      // If no nodes available, set high latency
      const latency = bestLatency === Number.POSITIVE_INFINITY
        ? 100 + Math.random() * 50
        : bestLatency;

      return {
        ...user,
        predictedPath,
        assignedEdge,
        assignedCentral,
        latency,
      };
    });

    setUsers(updatedUsers);

    const avgLatency =
      updatedUsers.reduce((sum, user) => sum + user.latency, 0) /
        updatedUsers.length || 0;
    setTotalLatency(Math.round(avgLatency));

    // Update edge node loads
    const updatedEdges = edgeNodes.map((edge) => {
      const assignedUsers = updatedUsers.filter(
        (user) => user.assignedEdge === edge.id
      );
      const load = (assignedUsers.length / (edge.capacity / 10)) * 100;
      return { ...edge, currentLoad: Math.min(100, load) };
    });
    setEdgeNodes(updatedEdges);

    // Update central node loads
    const updatedCentrals = centralNodes.map((central) => {
      const assignedUsers = updatedUsers.filter(
        (user) => user.assignedCentral === central.id
      );
      const load = (assignedUsers.length / (central.capacity / 10)) * 100;
      return { ...central, currentLoad: Math.min(100, load) };
    });
    setCentralNodes(updatedCentrals);
  }, [
    users,
    edgeNodes,
    centralNodes,
    predictionEnabled,
    selectedAlgorithm,
    predictionSteps,
    autoAssignment,
  ]);

  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    setUsers((prevUsers) =>
      prevUsers.map((user) => {
        let newX = user.x + user.vx * simulationSpeed[0];
        let newY = user.y + user.vy * simulationSpeed[0];
        let newVx = user.vx;
        let newVy = user.vy;

        if (newX <= 10 || newX >= window.innerWidth - 10) {
          newVx = -newVx;
          newX = Math.max(10, Math.min(window.innerWidth - 10, newX));
        }
        if (newY <= 10 || newY >= window.innerHeight - 10) {
          newVy = -newVy;
          newY = Math.max(10, Math.min(window.innerHeight - 10, newY));
        }

        return { ...user, x: newX, y: newY, vx: newVx, vy: newVy };
      })
    );
  }, [isSimulating, simulationSpeed]);

  // Handle canvas click to add users or select nodes
  const handleCanvasClick = (event) => {
    if (isDragging || isPanning || isDraggingNode || isDraggingUser) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const screenX = event.clientX - rect.left;
    const screenY = event.clientY - rect.top;
    const worldX = (screenX - panOffset.x) / zoomLevel;
    const worldY = (screenY - panOffset.y) / zoomLevel;

    // Check for node selection first
    const clickedEdge = edgeNodes.find(
      (edge) => calculateDistance(worldX, worldY, edge.x, edge.y) < 20
    );
    const clickedCentral = centralNodes.find(
      (central) => calculateDistance(worldX, worldY, central.x, central.y) < 25
    );
    const clickedUser = users.find(
      (user) =>
        calculateDistance(worldX, worldY, user.x, user.y) < user.size + 5
    );

    if (clickedEdge) {
      setSelectedEdge(clickedEdge);
      setSelectedCentral(null);
      setSelectedUser(null);
      return;
    }

    if (clickedCentral) {
      setSelectedCentral(clickedCentral);
      setSelectedEdge(null);
      setSelectedUser(null);
      return;
    }

    if (clickedUser) {
      setSelectedUser(clickedUser);
      setSelectedEdge(null);
      setSelectedCentral(null);
      return;
    }

    // Clear selections and add user if not in edit mode
    setSelectedUser(null);
    setSelectedEdge(null);
    setSelectedCentral(null);

    if (editMode === "none") {
      const newUser = {
        id: `user-${Date.now()}`,
        x: worldX,
        y: worldY,
        vx: (Math.random() - 0.5) * userSpeed[0],
        vy: (Math.random() - 0.5) * userSpeed[0],
        predictedPath: [],
        assignedEdge: null,
        assignedCentral: null,
        latency: 0,
        size: userSize[0],
        manualConnection: false,
      };
      setUsers((prev) => [...prev, newUser]);
    }
  };

  // Handle mouse down for dragging
  const handleMouseDown = (event) => {
    if (
      event.button === 1 ||
      (event.button === 0 && event.ctrlKey && editMode === "none")
    ) {
      setIsPanning(true);
      setLastPanPoint({ x: event.clientX, y: event.clientY });
      event.preventDefault();
      return;
    }

    if (editMode !== "none") {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      const worldX = (screenX - panOffset.x) / zoomLevel;
      const worldY = (screenY - panOffset.y) / zoomLevel;

      // Check for user dragging first (if users edit mode is enabled)
      if (editMode === "users" || editMode === "both") {
        const clickedUser = users.find(
          (user) =>
            calculateDistance(worldX, worldY, user.x, user.y) < user.size + 5
        );
        if (clickedUser) {
          setIsDraggingUser(true);
          setDraggedUser(clickedUser);
          setDragOffset({
            x: worldX - clickedUser.x,
            y: worldY - clickedUser.y,
          });
          event.preventDefault();
          return;
        }
      }

      // Check for node dragging (if nodes edit mode is enabled)
      if (editMode === "nodes" || editMode === "both") {
        const clickedEdge = edgeNodes.find(
          (edge) => calculateDistance(worldX, worldY, edge.x, edge.y) < 20
        );
        const clickedCentral = centralNodes.find(
          (central) =>
            calculateDistance(worldX, worldY, central.x, central.y) < 25
        );

        if (clickedEdge) {
          setIsDraggingNode(true);
          setDraggedNode({ type: "edge", node: clickedEdge });
          setDragOffset({
            x: worldX - clickedEdge.x,
            y: worldY - clickedEdge.y,
          });
          event.preventDefault();
          return;
        }

        if (clickedCentral) {
          setIsDraggingNode(true);
          setDraggedNode({ type: "central", node: clickedCentral });
          setDragOffset({
            x: worldX - clickedCentral.x,
            y: worldY - clickedCentral.y,
          });
          event.preventDefault();
          return;
        }
      }
    }

    setIsDragging(false);
    handleCanvasClick(event);
  };

  const handleMouseMove = (event) => {
    if (isPanning) {
      const deltaX = event.clientX - lastPanPoint.x;
      const deltaY = event.clientY - lastPanPoint.y;
      setPanOffset((prev) => ({
        x: prev.x + deltaX,
        y: prev.y + deltaY,
      }));
      setLastPanPoint({ x: event.clientX, y: event.clientY });
    } else if (isDraggingUser && draggedUser) {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      const worldX = (screenX - panOffset.x) / zoomLevel;
      const worldY = (screenY - panOffset.y) / zoomLevel;

      const newX = worldX - dragOffset.x;
      const newY = worldY - dragOffset.y;

      setUsers((prev) =>
        prev.map((user) =>
          user.id === draggedUser.id ? { ...user, x: newX, y: newY } : user
        )
      );

      // Update selected user if it's the one being dragged
      if (selectedUser && selectedUser.id === draggedUser.id) {
        setSelectedUser((prev) => ({ ...prev, x: newX, y: newY }));
      }
    } else if (isDraggingNode && draggedNode) {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      const worldX = (screenX - panOffset.x) / zoomLevel;
      const worldY = (screenY - panOffset.y) / zoomLevel;

      const newX = worldX - dragOffset.x;
      const newY = worldY - dragOffset.y;

      if (draggedNode.type === "edge") {
        setEdgeNodes((prev) =>
          prev.map((edge) =>
            edge.id === draggedNode.node.id
              ? { ...edge, x: newX, y: newY }
              : edge
          )
        );
      } else if (draggedNode.type === "central") {
        setCentralNodes((prev) =>
          prev.map((central) =>
            central.id === draggedNode.node.id
              ? { ...central, x: newX, y: newY }
              : central
          )
        );
      }
    } else {
      setIsDragging(true);
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setIsDraggingNode(false);
    setIsDraggingUser(false);
    setDraggedNode(null);
    setDraggedUser(null);
    setTimeout(() => setIsDragging(false), 100);
  };

  // Zoom functions
  const zoomIn = () => setZoomLevel((prev) => Math.min(prev * 1.2, 5));
  const zoomOut = () => setZoomLevel((prev) => Math.max(prev / 1.2, 0.2));
  const resetZoom = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  const handleWheel = (event) => {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.2, Math.min(5, zoomLevel * zoomFactor));

    const zoomRatio = newZoom / zoomLevel;
    const newPanX = mouseX - (mouseX - panOffset.x) * zoomRatio;
    const newPanY = mouseY - (mouseY - panOffset.y) * zoomRatio;

    setZoomLevel(newZoom);
    setPanOffset({ x: newPanX, y: newPanY });
  };

  // Drawing function with zoom and pan support
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(panOffset.x, panOffset.y);
    ctx.scale(zoomLevel, zoomLevel);

    const visibleLeft = -panOffset.x / zoomLevel;
    const visibleTop = -panOffset.y / zoomLevel;
    const visibleRight = (canvas.width - panOffset.x) / zoomLevel;
    const visibleBottom = (canvas.height - panOffset.y) / zoomLevel;

    // Draw grid
    ctx.strokeStyle = "#f0f0f0";
    ctx.lineWidth = 1 / zoomLevel;
    const gridSize = 50;
    const startX = Math.floor(visibleLeft / gridSize) * gridSize;
    const startY = Math.floor(visibleTop / gridSize) * gridSize;

    for (let i = startX; i <= visibleRight + gridSize; i += gridSize) {
      ctx.beginPath();
      ctx.moveTo(i, visibleTop);
      ctx.lineTo(i, visibleBottom);
      ctx.stroke();
    }
    for (let i = startY; i <= visibleBottom + gridSize; i += gridSize) {
      ctx.beginPath();
      ctx.moveTo(visibleLeft, i);
      ctx.lineTo(visibleRight, i);
      ctx.stroke();
    }

    // Draw connections between central and edge nodes
    centralNodes.forEach((central) => {
      edgeNodes.forEach((edge) => {
        ctx.strokeStyle = "rgba(99, 101, 241, 0.63)";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.setLineDash([10 / zoomLevel, 5 / zoomLevel]);
        ctx.beginPath();
        ctx.moveTo(central.x, central.y);
        ctx.lineTo(edge.x, edge.y);
        ctx.stroke();
        ctx.setLineDash([]);
      });
    });

    // Draw connections between edge nodes
    for (let i = 0; i < edgeNodes.length; i++) {
      for (let j = i + 1; j < edgeNodes.length; j++) {
        const edgeA = edgeNodes[i];
        const edgeB = edgeNodes[j];
        ctx.strokeStyle = "rgba(16, 185, 129, 0.6)"; // subtle green
        ctx.lineWidth = 1.5 / zoomLevel;
        ctx.setLineDash([6 / zoomLevel, 4 / zoomLevel]);
        ctx.beginPath();
        ctx.moveTo(edgeA.x, edgeA.y);
        ctx.lineTo(edgeB.x, edgeB.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    // Draw central nodes
    centralNodes.forEach((central) => {
      if (
        central.x + central.coverage < visibleLeft ||
        central.x - central.coverage > visibleRight ||
        central.y + central.coverage < visibleTop ||
        central.y - central.coverage > visibleBottom
      ) {
        return;
      }

      // Coverage area
      ctx.fillStyle = `rgba(99, 102, 241, ${
        0.03 + central.currentLoad * 0.002
      })`;
      ctx.beginPath();
      ctx.arc(central.x, central.y, central.coverage, 0, 2 * Math.PI);
      ctx.fill();

      // Central node
      const isSelected = selectedCentral && selectedCentral.id === central.id;
      ctx.fillStyle = isSelected
        ? "#8b5cf6"
        : central.currentLoad > 80
        ? "#dc2626"
        : central.currentLoad > 50
        ? "#ea580c"
        : "#6366f1";

      // Draw diamond shape for central nodes
      const size = isSelected ? 25 : 20;
      ctx.beginPath();
      ctx.moveTo(central.x, central.y - size);
      ctx.lineTo(central.x + size, central.y);
      ctx.lineTo(central.x, central.y + size);
      ctx.lineTo(central.x - size, central.y);
      ctx.closePath();
      ctx.fill();

      // Edit mode indicator for nodes
      if ((editMode === "nodes" || editMode === "both") && !isSelected) {
        ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.setLineDash([5 / zoomLevel, 5 / zoomLevel]);
        ctx.beginPath();
        ctx.arc(central.x, central.y, 30, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = "#8b5cf6";
        ctx.lineWidth = 3 / zoomLevel;
        ctx.beginPath();
        ctx.arc(central.x, central.y, 35, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Label
      const fontSize = Math.max(10, 14 / zoomLevel);
      ctx.fillStyle = "#374151";
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(central.id, central.x, central.y - 45);
      ctx.fillText(
        `${Math.round(central.currentLoad)}%`,
        central.x,
        central.y + 55
      );
    });

    // Draw edge nodes
    edgeNodes.forEach((edge) => {
      if (
        edge.x + edge.coverage < visibleLeft ||
        edge.x - edge.coverage > visibleRight ||
        edge.y + edge.coverage < visibleTop ||
        edge.y - edge.coverage > visibleBottom
      ) {
        return;
      }

      // Coverage area
      ctx.fillStyle = `rgba(59, 130, 246, ${0.05 + edge.currentLoad * 0.003})`;
      ctx.beginPath();
      ctx.arc(edge.x, edge.y, edge.coverage, 0, 2 * Math.PI);
      ctx.fill();

      // Edge node
      const isSelected = selectedEdge && selectedEdge.id === edge.id;
      ctx.fillStyle = isSelected
        ? "#8b5cf6"
        : edge.currentLoad > 80
        ? "#ef4444"
        : edge.currentLoad > 50
        ? "#f59e0b"
        : "#10b981";
      ctx.beginPath();
      ctx.arc(edge.x, edge.y, isSelected ? 20 : 15, 0, 2 * Math.PI);
      ctx.fill();

      // Edit mode indicator for nodes
      if ((editMode === "nodes" || editMode === "both") && !isSelected) {
        ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.setLineDash([5 / zoomLevel, 5 / zoomLevel]);
        ctx.beginPath();
        ctx.arc(edge.x, edge.y, 25, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = "#8b5cf6";
        ctx.lineWidth = 3 / zoomLevel;
        ctx.beginPath();
        ctx.arc(edge.x, edge.y, 25, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Label
      const fontSize = Math.max(10, 14 / zoomLevel);
      ctx.fillStyle = "#374151";
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(edge.id, edge.x, edge.y - 35);
      ctx.fillText(`${Math.round(edge.currentLoad)}%`, edge.x, edge.y + 45);
    });

    // Draw users and their predicted paths
    users.forEach((user) => {
      if (
        user.x < visibleLeft - 50 ||
        user.x > visibleRight + 50 ||
        user.y < visibleTop - 50 ||
        user.y > visibleBottom + 50
      ) {
        return;
      }

      // Predicted path
      if (predictionEnabled && user.predictedPath.length > 0) {
        ctx.strokeStyle = "rgba(168, 85, 247, 0.6)";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.setLineDash([5 / zoomLevel, 5 / zoomLevel]);
        ctx.beginPath();
        ctx.moveTo(user.x, user.y);
        user.predictedPath.forEach((point) => {
          ctx.lineTo(point.x, point.y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Connection to assigned edge (different style for manual connections)
      if (user.assignedEdge) {
        const assignedEdge = edgeNodes.find(
          (edge) => edge.id === user.assignedEdge
        );
        if (assignedEdge) {
          ctx.strokeStyle = user.manualConnection
            ? "rgba(34, 197, 94, 0.8)"
            : "rgba(34, 197, 94, 0.4)";
          ctx.lineWidth = user.manualConnection ? 2 / zoomLevel : 1 / zoomLevel;
          if (user.manualConnection) {
            ctx.setLineDash([]);
          }
          ctx.beginPath();
          ctx.moveTo(user.x, user.y);
          ctx.lineTo(assignedEdge.x, assignedEdge.y);
          ctx.stroke();
        }
      }

      // Connection to assigned central node (different style for manual connections)
      if (user.assignedCentral) {
        const assignedCentral = centralNodes.find(
          (central) => central.id === user.assignedCentral
        );
        if (assignedCentral) {
          ctx.strokeStyle = user.manualConnection
            ? "rgba(99, 102,241, 0.8)"
            : "rgba(99, 102,241, 0.4)";
          ctx.lineWidth = user.manualConnection ? 2 / zoomLevel : 1 / zoomLevel;
          if (user.manualConnection) {
            ctx.setLineDash([]);
          }
          ctx.beginPath();
          ctx.moveTo(user.x, user.y);
          ctx.lineTo(assignedCentral.x, assignedCentral.y);
          ctx.stroke();
        }
      }

      // User
      const isSelected = selectedUser && selectedUser.id === user.id;
      ctx.fillStyle = isSelected
        ? "#8b5cf6"
        : user.manualConnection
        ? "#f59e0b"
        : "#3b82f6";
      ctx.beginPath();
      ctx.arc(
        user.x,
        user.y,
        isSelected ? user.size + 2 : user.size,
        0,
        2 * Math.PI
      );
      ctx.fill();

      // Manual connection indicator
      if (user.manualConnection) {
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.beginPath();
        ctx.arc(user.x, user.y, user.size + 4, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Edit mode indicator for users
      if ((editMode === "users" || editMode === "both") && !isSelected) {
        ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.setLineDash([3 / zoomLevel, 3 / zoomLevel]);
        ctx.beginPath();
        ctx.arc(user.x, user.y, user.size + 8, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = "#8b5cf6";
        ctx.lineWidth = 2 / zoomLevel;
        ctx.beginPath();
        ctx.arc(user.x, user.y, user.size + 6, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Latency indicator
      const latencyColor =
        user.latency > 50
          ? "#ef4444"
          : user.latency > 25
          ? "#f59e0b"
          : "#10b981";
      ctx.fillStyle = latencyColor;
      ctx.beginPath();
      ctx.arc(user.x, user.y, 3, 0, 2 * Math.PI);
      ctx.fill();

      // User ID for selected user
      if (isSelected) {
        const fontSize = Math.max(8, 12 / zoomLevel);
        ctx.fillStyle = "#374151";
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(user.id, user.x, user.y - user.size - 10);
      }
    });

    ctx.restore();
  }, [
    users,
    edgeNodes,
    centralNodes,
    predictionEnabled,
    selectedUser,
    selectedEdge,
    selectedCentral,
    zoomLevel,
    panOffset,
    editMode,
  ]);

  // Animation loop
  useEffect(() => {
    const interval = setInterval(() => {
      simulationStep();
      optimizeReplicaPlacement();
      draw();
    }, 100);

    return () => clearInterval(interval);
  }, [simulationStep, optimizeReplicaPlacement, draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

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

  const resetSimulation = () => {
    clearEverything();
  };

  const addEdgeNode = () => {
    const newEdge = {
      id: `edge-${edgeNodes.length + 1}`,
      x: Math.random() * (window.innerWidth - 200) + 100,
      y: Math.random() * (window.innerHeight - 200) + 100,
      capacity: edgeCapacity[0],
      currentLoad: 0,
      replicas: [],
      coverage: edgeCoverage[0],
      isWarm: false,
      lastAccessTime: null,
      lastMetrics: null,
      type: "cloudlet"
    };
    setEdgeNodes((prev) => [...prev, newEdge]);
  };

  const removeEdgeNode = () => {
    if (edgeNodes.length > 0) {
      const nodeToRemove = edgeNodes[edgeNodes.length - 1];
      setEdgeNodes((prev) => prev.slice(0, -1));
      if (selectedEdge && selectedEdge.id === nodeToRemove.id) {
        setSelectedEdge(null);
      }
    }
  };

  const addCentralNode = () => {
    const newCentral = {
      id: `central-${centralNodes.length + 1}`,
      x: Math.random() * (window.innerWidth - 400) + 200,
      y: Math.random() * (window.innerHeight - 400) + 200,
      capacity: centralCapacity[0],
      currentLoad: 0,
      coverage: centralCoverage[0],
      type: "main",
      isWarm: false,
      lastAccessTime: null,
      lastMetrics: null,
      nodeType: "cloud"
    };
    setCentralNodes((prev) => [...prev, newCentral]);
  };

  const removeCentralNode = () => {
    if (centralNodes.length > 0) {
      setCentralNodes((prev) => prev.slice(0, -1));
      if (
        selectedCentral &&
        selectedCentral.id === `central-${centralNodes.length}`
      ) {
        setSelectedCentral(null);
      }
    }
  };

  const deleteSelectedNode = () => {
    if (selectedEdge) {
      setEdgeNodes((prev) =>
        prev.filter((edge) => edge.id !== selectedEdge.id)
      );
      setSelectedEdge(null);
    }
    if (selectedCentral) {
      setCentralNodes((prev) =>
        prev.filter((central) => central.id !== selectedCentral.id)
      );
      setSelectedCentral(null);
    }
  };

  const clearAllUsers = () => {
    setUsers([]);
    setSelectedUser(null);
  };

  const clearAllEdgeNodes = () => {
    setEdgeNodes([]);
    setSelectedEdge(null);
  };

  const clearAllCentralNodes = () => {
    setCentralNodes([]);
    setSelectedCentral(null);
  };

  const clearEverything = () => {
    setUsers([]);
    setEdgeNodes([]);
    setCentralNodes([]);
    setSelectedUser(null);
    setSelectedEdge(null);
    setSelectedCentral(null);
    setIsSimulating(false);
    setTotalLatency(0);
  };

  const getEditModeDescription = () => {
    switch (editMode) {
      case "nodes":
        return "Node Edit: Drag nodes to move • Click to select";
      case "users":
        return "User Edit: Drag users to move • Click to select";
      case "both":
        return "Full Edit: Drag nodes and users • Click to select";
      default:
        return "Click to add users • Mouse wheel to zoom • Ctrl+drag to pan the map";
    }
  };

  const getCursorStyle = () => {
    if (isPanning) return "grabbing";
    if (isDraggingNode || isDraggingUser) return "grabbing";
    if (editMode !== "none") return "move";
    return "crosshair";
  };

  return (
    <div className="relative w-full h-screen overflow-hidden bg-gray-50">
      {/* Full Screen Canvas */}
      <SimulationCanvas
        canvasRef={canvasRef}
        handleCanvasClick={handleCanvasClick}
        handleMouseDown={handleMouseDown}
        handleMouseMove={handleMouseMove}
        handleMouseUp={handleMouseUp}
        handleWheel={handleWheel}
        getCursorStyle={getCursorStyle}
      />

      {/* Left Control Panel */}
      <ControlPanel leftPanelOpen={leftPanelOpen}>
        <ControlPanelContent
          users={users}
          setUsers={setUsers}
          edgeNodes={edgeNodes}
          setEdgeNodes={setEdgeNodes}
          centralNodes={centralNodes}
          setCentralNodes={setCentralNodes}
          isSimulating={isSimulating}
          setIsSimulating={setIsSimulating}
          simulationSpeed={simulationSpeed}
          setSimulationSpeed={setSimulationSpeed}
          predictionEnabled={predictionEnabled}
          setPredictionEnabled={setPredictionEnabled}
          totalLatency={totalLatency}
          setTotalLatency={setTotalLatency}
          isDragging={isDragging}
          setIsDragging={setIsDragging}
          leftPanelOpen={leftPanelOpen}
          setLeftPanelOpen={setLeftPanelOpen}
          rightPanelOpen={rightPanelOpen}
          setRightPanelOpen={setRightPanelOpen}
          selectedAlgorithm={selectedAlgorithm}
          setSelectedAlgorithm={setSelectedAlgorithm}
          selectedUser={selectedUser}
          setSelectedUser={setSelectedUser}
          selectedEdge={selectedEdge}
          setSelectedEdge={setSelectedEdge}
          selectedCentral={selectedCentral}
          setSelectedCentral={setSelectedCentral}
          userSpeed={userSpeed}
          setUserSpeed={setUserSpeed}
          userSize={userSize}
          setUserSize={setUserSize}
          zoomIn={zoomIn}
          zoomOut={zoomOut}
          resetZoom={resetZoom}
          predictionSteps={predictionSteps}
          setPredictionSteps={setPredictionSteps}
          edgeCapacity={edgeCapacity}
          setEdgeCapacity={setEdgeCapacity}
          edgeCoverage={edgeCoverage}
          setEdgeCoverage={setEdgeCoverage}
          centralCapacity={centralCapacity}
          setCentralCapacity={setCentralCapacity}
          centralCoverage={centralCoverage}
          setCentralCoverage={setCentralCoverage}
          zoomLevel={zoomLevel}
          setZoomLevel={setZoomLevel}
          panOffset={panOffset}
          setPanOffset={setPanOffset}
          isPanning={isPanning}
          setIsPanning={setIsPanning}
          lastPanPoint={lastPanPoint}
          setLastPanPoint={setLastPanPoint}
          editMode={editMode}
          setEditMode={setEditMode}
          isDraggingNode={isDraggingNode}
          setIsDraggingNode={setIsDraggingNode}
          isDraggingUser={isDraggingUser}
          setIsDraggingUser={setIsDraggingUser}
          draggedNode={draggedNode}
          setDraggedNode={setDraggedNode}
          draggedUser={draggedUser}
          setDraggedUser={setDraggedUser}
          dragOffset={dragOffset}
          setDragOffset={setDragOffset}
          manualConnectionMode={manualConnectionMode}
          setManualConnectionMode={setManualConnectionMode}
          autoAssignment={autoAssignment}
          setAutoAssignment={setAutoAssignment}
          algorithms={algorithms}
          calculateDistance={calculateDistance}
          connectUserToNode={connectUserToNode}
          disconnectUser={disconnectUser}
          resetAllConnections={resetAllConnections}
          updateSelectedUser={updateSelectedUser}
          deleteSelectedUser={deleteSelectedUser}
          predictUserMobility={predictUserMobility}
          optimizeReplicaPlacement={optimizeReplicaPlacement}
          simulationStep={simulationStep}
          handleCanvasClick={handleCanvasClick}
          handleMouseDown={handleMouseDown}
          handleMouseMove={handleMouseMove}
          handleMouseUp={handleMouseUp}
          handleWheel={handleWheel}
          draw={draw}
          resetSimulation={resetSimulation}
          addEdgeNode={addEdgeNode}
          removeEdgeNode={removeEdgeNode}
          addCentralNode={addCentralNode}
          removeCentralNode={removeCentralNode}
          deleteSelectedNode={deleteSelectedNode}
          clearAllUsers={clearAllUsers}
          clearAllEdgeNodes={clearAllEdgeNodes}
          clearAllCentralNodes={clearAllCentralNodes}
          clearEverything={clearEverything}
          getEditModeDescription={getEditModeDescription}
          getCursorStyle={getCursorStyle}
          socketData={socketData}
        />
      </ControlPanel>

      {/* Right Metrics Panel */}
      <MetricsPanel rightPanelOpen={rightPanelOpen}>
        <MetricsPanelContent
          users={users}
          edgeNodes={edgeNodes}
          centralNodes={centralNodes}
          totalLatency={totalLatency}
          selectedUser={selectedUser}
          setSelectedUser={setSelectedUser}
          selectedEdge={selectedEdge}
          setSelectedEdge={setSelectedEdge}
          selectedCentral={selectedCentral}
          setSelectedCentral={setSelectedCentral}
          algorithms={algorithms}
          selectedAlgorithm={selectedAlgorithm}
          rightPanelOpen={rightPanelOpen}
          setRightPanelOpen={setRightPanelOpen}
        />
      </MetricsPanel>

      {/* Toggle Buttons for Panels */}
      {!leftPanelOpen && (
        <Button
          className="absolute left-4 top-4 z-20"
          size="sm"
          onClick={() => setLeftPanelOpen(true)}
        >
          <Settings className="w-4 h-4" />
        </Button>
      )}
      {!rightPanelOpen && (
        <Button
          className="absolute right-4 top-4 z-20"
          size="sm"
          onClick={() => setRightPanelOpen(true)}
        >
          <MapPin className="w-4 h-4" />
        </Button>
      )}

      {/* Instructions */}
      <EditModeDescription description={getEditModeDescription()} />
    </div>
  );
}
