import {
  updateStreetMapUsers,
  spawnNewStreetMapUsers,
  simulateServerlessFunctions,
  autoAssignStreetMapUsers
} from "./street-map-users";
import { updateTrafficLights } from "./road-network";
import { use, useCallback, useRef } from "react";
import useSimulationStore from "@/hooks/use-simulation-store";

// Simulation Functions
export const useSimulationLogic = (state, actions) => {
  const {
    roadMode,
    roads,
    roadNetwork,
    edgeNodes,
    centralNodes,
    assignmentAlgorithm,
    simulationMode,
  } = state;

  const { setUsers, setRoadNetwork, setTotalLatency } = actions;
  const { userSpeed, isSimulating, selectedScenario, simulationSpeed } = useSimulationStore();

  // Step counter for periodic operations in demo mode
  const stepCounterRef = useRef(0);

  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    // Handle street map scenario client-side simulation
    if (selectedScenario === "scenario4" && roadNetwork) {
      // Update traffic lights
      const updatedTrafficLights = updateTrafficLights(roadNetwork.trafficLights);
      setRoadNetwork(prevNetwork => ({
        ...prevNetwork,
        trafficLights: updatedTrafficLights
      }));

      // Update street map users
      setUsers(prevUsers => {
        let updatedUsers = updateStreetMapUsers(
          prevUsers,
          { ...roadNetwork, trafficLights: updatedTrafficLights },
          simulationSpeed[0]
        );

        // Auto-assign unassigned users to nodes
        updatedUsers = autoAssignStreetMapUsers(
          updatedUsers,
          edgeNodes,
          centralNodes,
          assignmentAlgorithm
        );

        // Simulate serverless function execution
        updatedUsers = simulateServerlessFunctions(
          updatedUsers,
          edgeNodes,
          centralNodes
        );

        // Spawn new users with controlled rate
        updatedUsers = spawnNewStreetMapUsers(
          updatedUsers,
          { ...roadNetwork, trafficLights: updatedTrafficLights },
          25, // max users (reduced for better performance)
          0.08, // spawn rate (reduced to control density)
          userSpeed[0],
          10 // user size
        );

        return updatedUsers;
      });

      return;
    }

    // For other scenarios, backend manages the simulation
    // Client-side simulation logic is disabled to avoid conflicts
    return;
  }, [isSimulating, simulationSpeed, roadMode, roads, userSpeed, setUsers, selectedScenario, roadNetwork, setRoadNetwork, edgeNodes, centralNodes, assignmentAlgorithm]);

  return {
    simulationStep
  };
};

export const getEditModeDescription = () => {
  const { editMode } = useSimulationStore();
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
