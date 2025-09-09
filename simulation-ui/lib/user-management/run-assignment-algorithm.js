import useGlobalState from "@/hooks/use-global-state";
import { calculateDistance } from "../helper";
import { calculateLatency } from "./placement-algorithms";

export const runAssignmentAlgorithm = () => {
  const { users, edgeNodes, centralNodes, assignmentAlgorithm, setUsers } =
    useGlobalState.getState();
  if (users.length === 0) {
    return;
  }

  if (edgeNodes.length === 0 && centralNodes.length === 0) {
    return;
  }

  setUsers((prevUsers) => {
    return prevUsers.map((user) => {
      let bestNode = null;
      let bestType = null;
      let bestLatency = Number.POSITIVE_INFINITY;

      switch (assignmentAlgorithm) {
        case "nearest-distance":
          // Find nearest node by distance
          let minDistance = Number.POSITIVE_INFINITY;

          edgeNodes.forEach((node) => {
            const distance = calculateDistance(user.x, user.y, node.x, node.y);
            if (distance < minDistance) {
              minDistance = distance;
              bestNode = node;
              bestType = "edge";
            }
          });

          centralNodes.forEach((node) => {
            const distance = calculateDistance(user.x, user.y, node.x, node.y);
            if (distance < minDistance) {
              minDistance = distance;
              bestNode = node;
              bestType = "central";
            }
          });
          break;

        case "nearest-latency":
          // Find node with minimum latency
          edgeNodes.forEach((node) => {
            const latency = calculateLatency(
              user,
              node.id,
              "edge",
              edgeNodes,
              centralNodes,
              window.__LATENCY_PARAMS__
            );
            if (latency < bestLatency) {
              bestLatency = latency;
              bestNode = node;
              bestType = "edge";
            }
          });

          centralNodes.forEach((node) => {
            const latency = calculateLatency(
              user,
              node.id,
              "central",
              edgeNodes,
              centralNodes,
              window.__LATENCY_PARAMS__
            );
            if (latency < bestLatency) {
              bestLatency = latency;
              bestNode = node;
              bestType = "central";
            }
          });
          break;

        case "gap-baseline":
          // Use GAP solver for this user
          const gapAssignment = solveGAP([user], edgeNodes, centralNodes, {
            method: "greedy",
            latencyParams: window.__LATENCY_PARAMS__,
            enableMemoryConstraints: false,
          });

          if (gapAssignment[user.id]) {
            const assignment = gapAssignment[user.id];
            bestNode = [...edgeNodes, ...centralNodes].find(
              (n) => n.id === assignment.nodeId
            );
            bestType = assignment.nodeType;
            bestLatency = assignment.latency;

            // Log GAP stats for debugging
            if (window.__GAP_DEBUG__) {
              const stats = getGAPStats(gapAssignment, [user]);
              console.log(`GAP assignment for ${user.id}:`, {
                nodeId: assignment.nodeId,
                nodeType: assignment.nodeType,
                profit: assignment.profit,
                latency: assignment.latency,
                stats,
              });
            }
          }
          break;


        default:
          console.warn(`Unknown assignment algorithm: ${assignmentAlgorithm}`);
          return user;
      }

      if (!bestNode) {
        return user;
      }

      const finalLatency =
        bestLatency !== Number.POSITIVE_INFINITY
          ? bestLatency
          : calculateLatency(
              user,
              bestNode.id,
              bestType,
              edgeNodes,
              centralNodes,
              window.__LATENCY_PARAMS__
            );

      return {
        ...user,
        assignedEdge: bestType === "edge" ? bestNode.id : null,
        assignedCentral: bestType === "central" ? bestNode.id : null,
        latency: finalLatency,
        manualConnection: false,
      };
    });
  });
};
