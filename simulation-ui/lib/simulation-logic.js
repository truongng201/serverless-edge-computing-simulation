import { useCallback } from "react";

// Simulation Functions
export const useSimulationLogic = (state, actions) => {
  const {
    isSimulating,
    simulationSpeed,
    roadMode,
    roads,
    userSpeed,
  } = state;

  const { setUsers } = actions;

  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    setUsers((prevUsers) =>
      prevUsers.map((user) => {
        // Skip movement for backend-controlled users
        if (user.isBackendControlled) {
          return user;
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
    default:
      return "Click to add users • Mouse wheel to zoom • Ctrl+drag to pan the map";
  }
};
