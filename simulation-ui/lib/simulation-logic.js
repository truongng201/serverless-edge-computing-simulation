import { useCallback, useRef } from "react";
import { calculateDistance } from "./helper";
import { calculateLatency } from "./placement-algorithms";

// Simulation Functions
export const useSimulationLogic = (state, actions) => {
  const {
    isSimulating,
    simulationSpeed,
    roadMode,
    roads,
    userSpeed,
    simulationMode,
    edgeNodes,
    centralNodes,
  } = state;

  const { setUsers, setTotalLatency } = actions;

  // Step counter for periodic operations in demo mode
  const stepCounterRef = useRef(0);

  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    // Increment step counter
    stepCounterRef.current += 1;
    const isReassignStep = simulationMode === "demo" && stepCounterRef.current % 5 === 0;

    let accumulatedLatency = 0;

    setUsers((prevUsers) =>
      prevUsers.map((user) => {
        // Movement (skip for backend-controlled users)
        if (!user.isBackendControlled) {
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

          user = { ...user, x: newX, y: newY, vx: newVx, vy: newVy };
        }

        // Demo mode: every 5 steps, (re)assign user to nearest edge (no coverage constraint, ignore manual)
        if (isReassignStep && edgeNodes && edgeNodes.length > 0) {
          let nearest = edgeNodes[0];
          let minDist = calculateDistance(user.x, user.y, edgeNodes[0].x, edgeNodes[0].y);
          for (let i = 1; i < edgeNodes.length; i++) {
            const d = calculateDistance(user.x, user.y, edgeNodes[i].x, edgeNodes[i].y);
            if (d < minDist) {
              minDist = d;
              nearest = edgeNodes[i];
            }
          }
          user = {
            ...user,
            assignedEdge: nearest?.id || null,
            assignedCentral: null,
            assignedNodeID: nearest?.id || null,
          };
        }

        // Compute latency each timestep based on current assignment
        let latency = 0;
        if (user.assignedEdge && edgeNodes && edgeNodes.length > 0) {
          latency = calculateLatency(user, user.assignedEdge, "edge", edgeNodes, centralNodes || []);
        } else if (user.assignedCentral && centralNodes && centralNodes.length > 0) {
          latency = calculateLatency(user, user.assignedCentral, "central", edgeNodes || [], centralNodes);
        } else if (simulationMode === "demo" && edgeNodes && edgeNodes.length > 0) {
          // If unassigned, estimate to nearest edge without persisting assignment
          let nearest = edgeNodes[0];
          let minDist = calculateDistance(user.x, user.y, edgeNodes[0].x, edgeNodes[0].y);
          for (let i = 1; i < edgeNodes.length; i++) {
            const d = calculateDistance(user.x, user.y, edgeNodes[i].x, edgeNodes[i].y);
            if (d < minDist) {
              minDist = d;
              nearest = edgeNodes[i];
            }
          }
          latency = calculateLatency(user, nearest.id, "edge", edgeNodes, centralNodes || []);
        }

        accumulatedLatency += latency;
        return { ...user, latency };
      })
    );

    // Update total latency aggregate
    setTotalLatency((prev) => {
      // Use the freshly accumulated latency for this step
      return accumulatedLatency;
    });
  }, [
    isSimulating,
    simulationSpeed,
    roadMode,
    roads,
    userSpeed,
    simulationMode,
    edgeNodes,
    centralNodes,
    setUsers,
    setTotalLatency,
  ]);

  return {
    simulationStep
  };
};

export const getEditModeDescription = (editMode) => {
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
