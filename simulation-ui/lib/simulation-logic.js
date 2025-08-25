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
    // When isSimulating is true, the backend manages the simulation
    // Client-side simulation logic is disabled to avoid conflicts
    if (!isSimulating) return;

    // All simulation logic is now handled by the backend API
    // This function only continues to exist for drawing/rendering purposes
    return;
  }, [isSimulating, simulationSpeed, roadMode, roads, userSpeed, setUsers]);

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
    case "drag":
      return "Drag Mode: Drag to pan the map • Mouse wheel to zoom";
    default:
      return "Click to add users • Mouse wheel to zoom";
  }
};
