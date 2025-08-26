import { useState, useRef, useEffect } from "react";
import { calculateLatency } from "../lib/placement-algorithms";

export function useSimulationState() {
  const [users, setUsers] = useState([]);
  const [edgeNodes, setEdgeNodes] = useState([]);
  const [centralNodes, setCentralNodes] = useState([]);


  // UI State
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);

  // Edge settings
  const [edgeCoverage, setEdgeCoverage] = useState([500]);

  // Central node settings
  const [centralCoverage, setCentralCoverage] = useState([0]);

  // Auto Placement state
  const [placementAlgorithm, setPlacementAlgorithm] = useState("topk-demand");
  
  // User Assignment state
  const [assignmentAlgorithm, setAssignmentAlgorithm] = useState("nearest-distance");


  // Periodic auto (re)assignment every 10s: pick min latency among all edges and centrals
  useEffect(() => {
    const interval = setInterval(() => {
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
  }, [edgeNodes, centralNodes, users]);


  return {
    users,
    setUsers,
    edgeNodes,
    setEdgeNodes,
    centralNodes,
    setCentralNodes,
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
    placementAlgorithm,
    setPlacementAlgorithm,
    assignmentAlgorithm,
    setAssignmentAlgorithm,
  };
}
