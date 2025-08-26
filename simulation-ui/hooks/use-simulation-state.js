import { useState, useRef, useEffect } from "react";
import { calculateLatency } from "../lib/placement-algorithms";

export function useSimulationState() {
  const [users, setUsers] = useState([]);
  const [edgeNodes, setEdgeNodes] = useState([]);
  const [centralNodes, setCentralNodes] = useState([]);

  const [totalLatency, setTotalLatency] = useState(0);

  // UI State
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);

  // Edge settings
  const [edgeCoverage, setEdgeCoverage] = useState([500]);

  // Central node settings
  const [centralCoverage, setCentralCoverage] = useState([0]);

  // Manual connection state
  const [autoAssignment, setAutoAssignment] = useState(true);

  // Live data state (only real mode now)
  const [liveData, setLiveData] = useState(null);

  // Auto Placement state
  const [placementAlgorithm, setPlacementAlgorithm] = useState("topk-demand");
  
  // User Assignment state
  const [assignmentAlgorithm, setAssignmentAlgorithm] = useState("nearest-distance");

  // Road Network state (for street map scenario)
  const [roadNetwork, setRoadNetwork] = useState(null);

  // Recalculate average latency whenever users update
  useEffect(() => {
    if (!users || users.length === 0) {
      setTotalLatency(0);
      return;
    }
    const sum = users.reduce((acc, u) => acc + (Number(u.latency) || 0), 0);
    setTotalLatency(Math.round(sum / users.length));
  }, [users, setTotalLatency]);

  // Periodic auto (re)assignment every 10s: pick min latency among all edges and centrals
  useEffect(() => {
    const interval = setInterval(() => {
      if (!autoAssignment) return;
      if ((edgeNodes?.length || 0) + (centralNodes?.length || 0) === 0) return;
      if (!users || users.length === 0) return;

      setUsers((prev) => prev.map((u) => {
        let bestLatency = Number.POSITIVE_INFINITY;
        let bestType = null;
        let bestId = null;

        // Evaluate all edges
        for (let i = 0; i < edgeNodes.length; i++) {
          const n = edgeNodes[i];
          const lat = calculateLatency(u, n.id, "edge", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
          if (lat < bestLatency) { bestLatency = lat; bestType = "edge"; bestId = n.id; }
        }

        // Evaluate all centrals
        for (let i = 0; i < centralNodes.length; i++) {
          const c = centralNodes[i];
          const lat = calculateLatency(u, c.id, "central", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
          if (lat < bestLatency) { bestLatency = lat; bestType = "central"; bestId = c.id; }
        }

        if (!bestType || !bestId || !isFinite(bestLatency)) return u;

        return {
          ...u,
          assignedEdge: bestType === "edge" ? bestId : null,
          assignedCentral: bestType === "central" ? bestId : null,
          latency: bestLatency,
        };
      }));
    }, 10000);

    return () => clearInterval(interval);
  }, [autoAssignment, edgeNodes, centralNodes, users]);

  // Note: Coverage updates are now handled individually per selected node in ControlPanelContent
  // This prevents the slider from affecting all nodes when only the selected one should change

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
    users,
    setUsers,
    edgeNodes,
    setEdgeNodes,
    centralNodes,
    setCentralNodes,
    totalLatency,
    setTotalLatency,
    selectedUser,
    setSelectedUser,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
    edgeCoverage,
    setEdgeCoverage,
    centralCoverage,
    setCentralCoverage,
    autoAssignment,
    setAutoAssignment,
    liveData,
    setLiveData,
    placementAlgorithm,
    setPlacementAlgorithm,
    assignmentAlgorithm,
    setAssignmentAlgorithm,
    roadNetwork,
    setRoadNetwork,
  };
}
