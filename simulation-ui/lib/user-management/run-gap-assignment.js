import useGlobalState from "@/hooks/use-global-state";
import { solveGAP, getGAPStats } from "./gap-solver";

// Run GAP assignment for all users (more efficient than per-user)
export const runGAPAssignment = () => {
  const { users, edgeNodes, centralNodes, setUsers } = useGlobalState();
  if (users.length === 0) {
    return;
  }

  if (edgeNodes.length === 0 && centralNodes.length === 0) {
    return;
  }

  const {
    method = "greedy",
    enableMemoryConstraints = false,
    debug = false,
  } = options;

  try {
    // Solve GAP for all users simultaneously
    const gapAssignment = solveGAP(users, edgeNodes, centralNodes, {
      method,
      latencyParams: window.__LATENCY_PARAMS__,
      enableMemoryConstraints,
    });

    // Apply assignment results
    setUsers((prevUsers) => {
      return prevUsers.map((user) => {
        const assignment = gapAssignment[user.id];
        if (!assignment) {
          return user; // No assignment found, keep current state
        }

        return {
          ...user,
          assignedEdge:
            assignment.nodeType === "edge" ? assignment.nodeId : null,
          assignedCentral:
            assignment.nodeType === "central" ? assignment.nodeId : null,
          latency: assignment.latency,
          manualConnection: false,
        };
      });
    });

    // Log stats if debug enabled
    if (debug || window.__GAP_DEBUG__) {
      const stats = getGAPStats(gapAssignment, users);
      console.log("GAP Assignment completed:", stats);
      console.log("Individual assignments:", gapAssignment);
    }

    console.log(
      `GAP assignment completed for ${Object.keys(gapAssignment).length}/${
        users.length
      } users`
    );
  } catch (error) {
    console.error("GAP assignment failed:", error);
  }
};
