import {
  updateStreetMapUsers,
  // spawnNewStreetMapUsers,
  spawnStreetUsersByTime,
  simulateServerlessFunctions,
  autoAssignStreetMapUsers,
} from "./street-map-users";
import { updateTrafficLights } from "./road-network";
import { useCallback, useRef } from "react";
import useGlobalState from "@/hooks/use-global-state";

// Simulation Functions
export const useSimulationLogic = () => {

  const {
    userSpeed,
    isSimulating,
    selectedScenario,
    simulationSpeed,
    roadNetwork,
    setRoadNetwork,
    edgeNodes,
    assignmentAlgorithm,
    centralNodes,
    setUsers,
    roadMode,
    roads,
    streetSpawnRate,
    streetMaxUsers,
    lastStreetSpawnAt,
    setLastStreetSpawnAt
  } = useGlobalState();

  // Simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulating) return;

    // Handle street map scenario client-side simulation
    if (selectedScenario === "scenario4" && roadNetwork) {
      // Update traffic lights
      const updatedTrafficLights = updateTrafficLights(
        roadNetwork.trafficLights,
        simulationSpeed?.[0] ?? 1
      );
      setRoadNetwork((prevNetwork) => ({
        ...prevNetwork,
        trafficLights: updatedTrafficLights,
      }));

      // Update street map users
      setUsers((prevUsers) => {
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

        // Spawn new users using real-time rate (users/sec)
        const now = Date.now();
        const spawnPerSecond = streetSpawnRate?.[0] ?? 0.5;
        const maxUsers = streetMaxUsers?.[0] ?? 15;
        const result = spawnStreetUsersByTime(
          updatedUsers,
          { ...roadNetwork, trafficLights: updatedTrafficLights },
          maxUsers,
          spawnPerSecond,
          userSpeed?.[0] ?? 5,
          10,
          now,
          lastStreetSpawnAt
        );
        updatedUsers = result.users;
        // Update last spawn time in global state
        setLastStreetSpawnAt(result.lastSpawnAt);

        return updatedUsers;
      });

      return;
    }

    // For other scenarios, backend manages the simulation
    // Client-side simulation logic is disabled to avoid conflicts
    return;
  }, [
    isSimulating,
    simulationSpeed,
    roadMode,
    roads,
    userSpeed,
    setUsers,
    selectedScenario,
    roadNetwork,
    setRoadNetwork,
    edgeNodes,
    centralNodes,
    assignmentAlgorithm,
    streetSpawnRate,
    streetMaxUsers,
    lastStreetSpawnAt,
    setLastStreetSpawnAt,
  ]);

  return {
    simulationStep,
  };
};
