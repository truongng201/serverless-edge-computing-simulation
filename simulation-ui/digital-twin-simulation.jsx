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
import { useSocket } from "@/hooks/use-socket";
import axios from 'axios';

export default function Component() {
  const canvasRef = useRef(null);
  const [users, setUsers] = useState([]);
  const [edgeNodes, setEdgeNodes] = useState([]);

  // Central nodes - main servers/coordinators
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

  // Auto Placement state
  const [placementAlgorithm, setPlacementAlgorithm] = useState("topk-demand");
  const [maxCoverageDistance, setMaxCoverageDistance] = useState([100]);

  // Road Network state
  const [roadMode, setRoadMode] = useState(false);
  const [roads, setRoads] = useState([]);
  const [showRoads, setShowRoads] = useState(true);

  // Socket.IO for real-time data communication
  const socketData = useSocket('http://localhost:5001', isSimulating);

  // Models for user expectancy calculation
  const models = {
    lstm: "LSTM",
  };


  const calculateDistance = (x1, y1, x2, y2) => {
    const dx = x2 - x1;
    const dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  };

  // Road Network Functions
  const createPredefinedRoads = () => {
    const canvasWidth = window.innerWidth;
    const canvasHeight = window.innerHeight;
    
    const predefinedRoads = [
      // Horizontal roads
      {
        id: "road-1",
        startX: 100,
        startY: 200,
        endX: canvasWidth - 100,
        endY: 200,
        width: 40,
        color: "#6B7280",
        type: "highway",
        direction: "bidirectional"
      },
      {
        id: "road-2", 
        startX: 150,
        startY: 400,
        endX: canvasWidth - 150,
        endY: 400,
        width: 30,
        color: "#9CA3AF",
        type: "main",
        direction: "bidirectional"
      },
      {
        id: "road-3",
        startX: 100,
        startY: 600,
        endX: canvasWidth - 200,
        endY: 600,
        width: 25,
        color: "#D1D5DB",
        type: "local",
        direction: "bidirectional"
      },
      // Vertical roads
      {
        id: "road-4",
        startX: 300,
        startY: 100,
        endX: 300,
        endY: canvasHeight - 100,
        width: 35,
        color: "#6B7280",
        type: "highway",
        direction: "bidirectional"
      },
      {
        id: "road-5",
        startX: 600,
        startY: 150,
        endX: 600,
        endY: canvasHeight - 150,
        width: 30,
        color: "#9CA3AF",
        type: "main",
        direction: "bidirectional"
      },
      {
        id: "road-6",
        startX: 900,
        startY: 100,
        endX: 900,
        endY: canvasHeight - 200,
        width: 25,
        color: "#D1D5DB",
        type: "local",
        direction: "bidirectional"
      }
    ];
    
    setRoads(predefinedRoads);
  };

  // Initialize roads on component mount
  useEffect(() => {
    createPredefinedRoads();
  }, []);

  // Get nearest point on a road to given coordinates
  const getNearestPointOnRoad = (x, y, road) => {
    const dx = road.endX - road.startX;
    const dy = road.endY - road.startY;
    const length = Math.sqrt(dx * dx + dy * dy);
    
    if (length === 0) return { x: road.startX, y: road.startY, t: 0 };
    
    const t = Math.max(0, Math.min(1, ((x - road.startX) * dx + (y - road.startY) * dy) / (length * length)));
    
    return {
      x: road.startX + t * dx,
      y: road.startY + t * dy,
      t: t
    };
  };

  // Find nearest road to given coordinates
  const findNearestRoad = (x, y) => {
    let nearestRoad = null;
    let minDistance = Infinity;
    let nearestPoint = null;
    
    roads.forEach(road => {
      const point = getNearestPointOnRoad(x, y, road);
      const distance = calculateDistance(x, y, point.x, point.y);
      
      if (distance < minDistance) {
        minDistance = distance;
        nearestRoad = road;
        nearestPoint = point;
      }
    });
    
    return { road: nearestRoad, point: nearestPoint, distance: minDistance };
  };

  // Move user along road
  const moveUserAlongRoad = (user, road) => {
    const dx = road.endX - road.startX;
    const dy = road.endY - road.startY;
    const length = Math.sqrt(dx * dx + dy * dy);
    
    if (length === 0) return { x: user.x, y: user.y };
    
    // Normalize direction
    const unitX = dx / length;
    const unitY = dy / length;
    
    // Move along road direction
    const speed = userSpeed[0];
    let newX = user.x + unitX * speed * (user.roadDirection || 1);
    let newY = user.y + unitY * speed * (user.roadDirection || 1);
    
    // Check bounds and reverse direction if needed
    const newPoint = getNearestPointOnRoad(newX, newY, road);
    if (newPoint.t <= 0 || newPoint.t >= 1) {
      // Reverse direction
      const newDirection = -(user.roadDirection || 1);
      newX = user.x + unitX * speed * newDirection;
      newY = user.y + unitY * speed * newDirection;
      return { 
        x: newX, 
        y: newY, 
        roadDirection: newDirection,
        constrainedToRoad: true 
      };
    }
    
    return { 
      x: newX, 
      y: newY, 
      roadDirection: user.roadDirection || 1,
      constrainedToRoad: true 
    };
  };

  // Auto Placement Algorithms
  const topKDemandPlacement = (users, candidates, k, lMax) => {
    // Calculate demand score for each candidate
    const candidateScores = candidates.map((candidate) => {
      const score = users.reduce((total, user) => {
        const distance = calculateDistance(user.x, user.y, candidate.x, candidate.y);
        return distance <= lMax ? total + 1 : total; // weight = 1 for all users
      }, 0);
      return { ...candidate, score };
    });

    // Sort by score descending and take top K
    candidateScores.sort((a, b) => b.score - a.score);
    return candidateScores.slice(0, k);
  };

  const kMeansPlacement = (users, candidates, k) => {
    if (users.length === 0) return [];
    
    // Simple K-means implementation
    // Initialize centroids randomly from users
    let centroids = [];
    const shuffledUsers = [...users].sort(() => Math.random() - 0.5);
    for (let i = 0; i < Math.min(k, shuffledUsers.length); i++) {
      centroids.push({ x: shuffledUsers[i].x, y: shuffledUsers[i].y });
    }

    // K-means iterations
    for (let iter = 0; iter < 10; iter++) {
      // Assign users to nearest centroid
      const clusters = Array(k).fill().map(() => []);
      users.forEach(user => {
        let minDist = Infinity;
        let assignedCluster = 0;
        centroids.forEach((centroid, idx) => {
          const dist = calculateDistance(user.x, user.y, centroid.x, centroid.y);
          if (dist < minDist) {
            minDist = dist;
            assignedCluster = idx;
          }
        });
        clusters[assignedCluster].push(user);
      });

      // Update centroids
      const newCentroids = clusters.map(cluster => {
        if (cluster.length === 0) return centroids[0]; // Handle empty cluster
        const avgX = cluster.reduce((sum, user) => sum + user.x, 0) / cluster.length;
        const avgY = cluster.reduce((sum, user) => sum + user.y, 0) / cluster.length;
        return { x: avgX, y: avgY };
      });

      centroids = newCentroids;
    }

    // Find nearest candidate for each centroid
    return centroids.map(centroid => {
      let nearestCandidate = candidates[0];
      let minDist = calculateDistance(centroid.x, centroid.y, candidates[0].x, candidates[0].y);
      
      candidates.forEach(candidate => {
        const dist = calculateDistance(centroid.x, centroid.y, candidate.x, candidate.y);
        if (dist < minDist) {
          minDist = dist;
          nearestCandidate = candidate;
        }
      });
      
      return nearestCandidate;
    });
  };

  const randomRandomPlacement = (users, candidates, k) => {
    // Random K candidates
    const shuffledCandidates = [...candidates].sort(() => Math.random() - 0.5);
    return shuffledCandidates.slice(0, k);
  };

  const randomNearestPlacement = (users, candidates, k) => {
    // Same as random-random for placement, difference is in assignment
    return randomRandomPlacement(users, candidates, k);
  };

  // Main placement algorithm runner
  const runPlacementAlgorithm = () => {
    if (users.length === 0) {
      alert("No users available for placement algorithm");
      return;
    }

    const k = edgeNodes.length;
    if (k === 0) {
      alert("No edge nodes available for placement");
      return;
    }

    // Use user positions as candidates
    const candidates = users.map(user => ({ x: user.x, y: user.y }));
    let selectedPositions = [];

    switch (placementAlgorithm) {
      case "topk-demand":
        selectedPositions = topKDemandPlacement(users, candidates, k, maxCoverageDistance[0]);
        break;
      case "kmeans":
        selectedPositions = kMeansPlacement(users, candidates, k);
        break;
      case "random-random":
        selectedPositions = randomRandomPlacement(users, candidates, k);
        break;
      case "random-nearest":
        selectedPositions = randomNearestPlacement(users, candidates, k);
        break;
      default:
        alert("Unknown placement algorithm");
        return;
    }

    // Update edge node positions
    setEdgeNodes(prevNodes => {
      return prevNodes.map((node, index) => {
        if (index < selectedPositions.length) {
          return {
            ...node,
            x: selectedPositions[index].x,
            y: selectedPositions[index].y
          };
        }
        return node;
      });
    });

    // Reassign users to nearest edge nodes
    const updatedNodes = edgeNodes.map((node, index) => {
      if (index < selectedPositions.length) {
        return {
          ...node,
          x: selectedPositions[index].x,
          y: selectedPositions[index].y
        };
      }
      return node;
    });

    setUsers(prevUsers => {
      return prevUsers.map(user => {
        if (placementAlgorithm === "random-random") {
          // Random assignment for random-random
          const randomNode = updatedNodes[Math.floor(Math.random() * updatedNodes.length)];
          return {
            ...user,
            assignedEdge: randomNode.id,
            assignedCentral: null,
            manualConnection: false,
            latency: calculateLatency(user, randomNode.id, "edge")
          };
        } else {
          // Nearest assignment for other algorithms
          let nearestNode = updatedNodes[0];
          let minDist = calculateDistance(user.x, user.y, updatedNodes[0].x, updatedNodes[0].y);
          
          updatedNodes.forEach(node => {
            const dist = calculateDistance(user.x, user.y, node.x, node.y);
            if (dist < minDist) {
              minDist = dist;
              nearestNode = node;
            }
          });

          return {
            ...user,
            assignedEdge: nearestNode.id,
            assignedCentral: null,
            manualConnection: false,
            latency: calculateLatency(user, nearestNode.id, "edge")
          };
        }
      });
    });

    console.log(`Placement algorithm ${placementAlgorithm} completed with ${selectedPositions.length} positions`);
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



  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    setUsers((prevUsers) =>
      prevUsers.map((user) => {
        // Road-constrained movement
        if (roadMode && user.assignedRoad) {
          const road = roads.find(r => r.id === user.assignedRoad);
          if (road) {
            const movement = moveUserAlongRoad(user, road);
            return {
              ...user,
              x: movement.x,
              y: movement.y,
              roadDirection: movement.roadDirection,
              constrainedToRoad: movement.constrainedToRoad
            };
          }
        }

        // Free movement (original logic)
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
  }, [isSimulating, simulationSpeed, roadMode, roads, userSpeed]);

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
      let userX = worldX;
      let userY = worldY;
      let assignedRoad = null;
      let roadDirection = Math.random() > 0.5 ? 1 : -1;

      // If road mode is enabled, snap user to nearest road
      if (roadMode && roads.length > 0) {
        const nearest = findNearestRoad(worldX, worldY);
        if (nearest.road && nearest.distance < 50) { // Allow placing within 50px of road
          userX = nearest.point.x;
          userY = nearest.point.y;
          assignedRoad = nearest.road.id;
        }
      }

      const newUser = {
        id: `user-${Date.now()}`,
        x: userX,
        y: userY,
        vx: roadMode ? 0 : (Math.random() - 0.5) * userSpeed[0], // No random velocity in road mode
        vy: roadMode ? 0 : (Math.random() - 0.5) * userSpeed[0],
        predictedPath: [],
        assignedEdge: null,
        assignedCentral: null,
        latency: 0,
        size: userSize[0],
        manualConnection: false,
        assignedRoad: assignedRoad,
        roadDirection: roadDirection,
        constrainedToRoad: roadMode && assignedRoad !== null
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

    // Draw roads
    if (showRoads && roads.length > 0) {
      roads.forEach((road) => {
        // Check if road is visible
        const roadLeft = Math.min(road.startX, road.endX) - road.width;
        const roadRight = Math.max(road.startX, road.endX) + road.width;
        const roadTop = Math.min(road.startY, road.endY) - road.width;
        const roadBottom = Math.max(road.startY, road.endY) + road.width;
        
        if (roadRight < visibleLeft || roadLeft > visibleRight || 
            roadBottom < visibleTop || roadTop > visibleBottom) {
          return;
        }

        // Draw road background (wider)
        ctx.strokeStyle = "#374151";
        ctx.lineWidth = (road.width + 4) / zoomLevel;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(road.startX, road.startY);
        ctx.lineTo(road.endX, road.endY);
        ctx.stroke();

        // Draw road surface
        ctx.strokeStyle = road.color;
        ctx.lineWidth = road.width / zoomLevel;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(road.startX, road.startY);
        ctx.lineTo(road.endX, road.endY);
        ctx.stroke();

        // Draw center line for highways and main roads
        if (road.type === "highway" || road.type === "main") {
          ctx.strokeStyle = "#FFFFFF";
          ctx.lineWidth = 2 / zoomLevel;
          ctx.setLineDash([20 / zoomLevel, 10 / zoomLevel]);
          ctx.beginPath();
          ctx.moveTo(road.startX, road.startY);
          ctx.lineTo(road.endX, road.endY);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Draw road labels
        if (zoomLevel > 0.5) {
          const midX = (road.startX + road.endX) / 2;
          const midY = (road.startY + road.endY) / 2;
          const fontSize = Math.max(8, 12 / zoomLevel);
          
          ctx.fillStyle = "#FFFFFF";
          ctx.font = `bold ${fontSize}px sans-serif`;
          ctx.textAlign = "center";
          ctx.strokeStyle = "#000000";
          ctx.lineWidth = 3 / zoomLevel;
          ctx.strokeText(road.id, midX, midY);
          ctx.fillText(road.id, midX, midY);
        }
      });
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
      if (central.coverage > 0) {
        ctx.fillStyle = `rgba(99, 102, 241, ${
          0.15 + central.currentLoad * 0.005
        })`;
        ctx.strokeStyle = `rgba(99, 102, 241, 0.4)`;
        ctx.lineWidth = 2 / zoomLevel;
        ctx.beginPath();
        ctx.arc(central.x, central.y, central.coverage, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      }

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
      if (edge.coverage > 0) {
        ctx.fillStyle = `rgba(16, 185, 129, ${0.12 + edge.currentLoad * 0.004})`;
        ctx.strokeStyle = `rgba(16, 185, 129, 0.5)`;
        ctx.lineWidth = 1.5 / zoomLevel;
        ctx.beginPath();
        ctx.arc(edge.x, edge.y, edge.coverage, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      }

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
    console.log(users);
    // Draw users and their predicted paths
    // Add logging to debug user visibility
    console.log('Users state:', users);
    users.forEach((user) => {
      console.log(`Rendering user: ${user.id}, Position: (${user.x}, ${user.y}), Size: ${user.size}`);
      if (
        user.x < visibleLeft - 50 ||
        user.x > visibleRight + 50 ||
        user.y < visibleTop - 50 ||
        user.y > visibleBottom + 50
      ) {
        console.log(`User ${user.id} is outside visible bounds.`);
        return;
      }

      // Connection to assigned edge (different style for manual connections)
      // if (user.assignedEdge) {
      //   const assignedEdge = edgeNodes.find(
      //     (edge) => edge.id === user.assignedEdge
      //   );
      //   if (assignedEdge) {
      //     ctx.strokeStyle = user.manualConnection
      //       ? "rgba(34, 197, 94, 0.8)"
      //       : "rgba(34, 197, 94, 0.4)";
      //     ctx.lineWidth = user.manualConnection ? 2 / zoomLevel : 1 / zoomLevel;
      //     if (user.manualConnection) {
      //       ctx.setLineDash([]);
      //     }
      //     ctx.beginPath();
      //     ctx.moveTo(user.x, user.y);
      //     ctx.lineTo(assignedEdge.x, assignedEdge.y);
      //     ctx.stroke();
      //   }
      // }

      // Connection to assigned central node (different style for manual connections)
      // if (user.assignedCentral) {
      //   const assignedCentral = centralNodes.find(
      //     (central) => central.id === user.assignedCentral
      //   );
      //   if (assignedCentral) {
      //     ctx.strokeStyle = user.manualConnection
      //       ? "rgba(99, 102,241, 0.8)"
      //       : "rgba(99, 102,241, 0.4)";
      //     ctx.lineWidth = user.manualConnection ? 2 / zoomLevel : 1 / zoomLevel;
      //     if (user.manualConnection) {
      //       ctx.setLineDash([]);
      //     }
      //     ctx.beginPath();
      //     ctx.moveTo(user.x, user.y);
      //     ctx.lineTo(assignedCentral.x, assignedCentral.y);
      //     ctx.stroke();
      //   }
      // }

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
    roadMode,
    roads,
    showRoads,
  ]);

  // Animation loop
  useEffect(() => {
    const interval = setInterval(() => {
      simulationStep();
      draw();
    }, 100);

    return () => clearInterval(interval);
  }, [simulationStep, draw]);

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

  // Cleanup socket connection on component unmount
  useEffect(() => {
    return () => {
      if (socketData && socketData.disconnect) {
        socketData.disconnect();
      }
    };
  }, [socketData]);

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

  // Fetch the first step of all users from the API
  useEffect(() => {
    const fetchFirstSample = async () => {
      try {
        const response = await axios.get('http://localhost:5001/get_first_sample');
        const firstSample = response.data;
        console.log('First Sample:', firstSample);
        // Update the users state with the fetched data
        setUsers(firstSample?.data?.items || []);
      } catch (error) {
        console.error('Error fetching first sample:', error);
      }
    };

    fetchFirstSample();
  }, []);

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
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
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
          models={models}
          calculateDistance={calculateDistance}
          connectUserToNode={connectUserToNode}
          disconnectUser={disconnectUser}
          resetAllConnections={resetAllConnections}
          updateSelectedUser={updateSelectedUser}
          deleteSelectedUser={deleteSelectedUser}
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
          placementAlgorithm={placementAlgorithm}
          setPlacementAlgorithm={setPlacementAlgorithm}
          maxCoverageDistance={maxCoverageDistance}
          setMaxCoverageDistance={setMaxCoverageDistance}
          runPlacementAlgorithm={runPlacementAlgorithm}
          roadMode={roadMode}
          setRoadMode={setRoadMode}
          showRoads={showRoads}
          setShowRoads={setShowRoads}
          roads={roads}
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
          models={models}
          selectedModel={selectedModel}
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
