import { 
  topKDemandPlacement, 
  kMeansPlacement, 
  randomRandomPlacement, 
  randomNearestPlacement,
  calculateLatency 
} from "./placement-algorithms";
import { calculateDistance } from "./helper";
import { solveGAP, getGAPStats } from "./gap-solver";

// Main placement algorithm runner
export const runPlacementAlgorithm = (
  users, 
  edgeNodes, 
  placementAlgorithm, 
  maxCoverageDistance, 
  setEdgeNodes, 
  setUsers
) => {
  if (users.length === 0) {
    return;
  }

  const k = edgeNodes.length;
  if (k === 0) {
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
          latency: calculateLatency(user, randomNode.id, "edge", updatedNodes, [])
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
          latency: calculateLatency(user, nearestNode.id, "edge", updatedNodes, [])
        };
      }
    });
  });

  console.log(`Placement algorithm ${placementAlgorithm} completed with ${selectedPositions.length} positions`);
};

// Run user assignment algorithm
export const runAssignmentAlgorithm = (
  users,
  edgeNodes,
  centralNodes,
  assignmentAlgorithm,
  setUsers
) => {
  if (users.length === 0) {
    alert("No users available for assignment");
    return;
  }

  if (edgeNodes.length === 0 && centralNodes.length === 0) {
    alert("No nodes available for assignment");
    return;
  }

  setUsers(prevUsers => {
    return prevUsers.map(user => {
      let bestNode = null;
      let bestType = null;
      let bestLatency = Number.POSITIVE_INFINITY;

      switch (assignmentAlgorithm) {
        case "nearest-distance":
          // Find nearest node by distance
          let minDistance = Number.POSITIVE_INFINITY;
          
          edgeNodes.forEach(node => {
            const distance = calculateDistance(user.x, user.y, node.x, node.y);
            if (distance < minDistance) {
              minDistance = distance;
              bestNode = node;
              bestType = "edge";
            }
          });

          centralNodes.forEach(node => {
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
          edgeNodes.forEach(node => {
            const latency = calculateLatency(user, node.id, "edge", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
            if (latency < bestLatency) {
              bestLatency = latency;
              bestNode = node;
              bestType = "edge";
            }
          });

          centralNodes.forEach(node => {
            const latency = calculateLatency(user, node.id, "central", edgeNodes, centralNodes, window.__LATENCY_PARAMS__);
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
            method: 'greedy',
            latencyParams: window.__LATENCY_PARAMS__,
            enableMemoryConstraints: false
          });
          
          if (gapAssignment[user.id]) {
            const assignment = gapAssignment[user.id];
            bestNode = [...edgeNodes, ...centralNodes].find(n => n.id === assignment.nodeId);
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
                stats
              });
            }
          }
          break;

        case "random":
          // Random assignment
          const allNodes = [
            ...edgeNodes.map(n => ({...n, type: "edge"})),
            ...centralNodes.map(n => ({...n, type: "central"}))
          ];
          if (allNodes.length > 0) {
            const randomNode = allNodes[Math.floor(Math.random() * allNodes.length)];
            bestNode = randomNode;
            bestType = randomNode.type;
          }
          break;

        default:
          console.warn(`Unknown assignment algorithm: ${assignmentAlgorithm}`);
          return user;
      }

      if (!bestNode) {
        return user;
      }

      const finalLatency = bestLatency !== Number.POSITIVE_INFINITY 
        ? bestLatency 
        : calculateLatency(user, bestNode.id, bestType, edgeNodes, centralNodes, window.__LATENCY_PARAMS__);

      return {
        ...user,
        assignedEdge: bestType === "edge" ? bestNode.id : null,
        assignedCentral: bestType === "central" ? bestNode.id : null,
        latency: finalLatency,
        manualConnection: false
      };
    });
  });

  console.log(`Assignment algorithm ${assignmentAlgorithm} completed`);
};

// Run GAP assignment for all users (more efficient than per-user)
export const runGAPAssignment = (
  users,
  edgeNodes, 
  centralNodes,
  setUsers,
  options = {}
) => {
  if (users.length === 0) {
    alert("No users available for GAP assignment");
    return;
  }

  if (edgeNodes.length === 0 && centralNodes.length === 0) {
    alert("No nodes available for GAP assignment");
    return;
  }

  const {
    method = 'greedy',
    enableMemoryConstraints = false,
    debug = false
  } = options;

  try {
    // Solve GAP for all users simultaneously
    const gapAssignment = solveGAP(users, edgeNodes, centralNodes, {
      method,
      latencyParams: window.__LATENCY_PARAMS__,
      enableMemoryConstraints
    });

    // Apply assignment results
    setUsers(prevUsers => {
      return prevUsers.map(user => {
        const assignment = gapAssignment[user.id];
        if (!assignment) {
          return user; // No assignment found, keep current state
        }

        return {
          ...user,
          assignedEdge: assignment.nodeType === "edge" ? assignment.nodeId : null,
          assignedCentral: assignment.nodeType === "central" ? assignment.nodeId : null,
          latency: assignment.latency,
          manualConnection: false
        };
      });
    });

    // Log stats if debug enabled
    if (debug || window.__GAP_DEBUG__) {
      const stats = getGAPStats(gapAssignment, users);
      console.log("GAP Assignment completed:", stats);
      console.log("Individual assignments:", gapAssignment);
    }

    console.log(`GAP assignment completed for ${Object.keys(gapAssignment).length}/${users.length} users`);
    
  } catch (error) {
    console.error("GAP assignment failed:", error);
  }
};

// Delete selected user
export const deleteSelectedUser = async (selectedUser, setUsers, setSelectedUser) => {
  if (!selectedUser) return;
  try {
    // Call API to delete user if API URL is available
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_user/${selectedUser.id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        console.error('Failed to delete user from server:', response.statusText);
      } else {
        console.log('User deleted successfully from server');
      }
    }
  } catch (error) {
    console.error('Error deleting user from server:', error);
  }
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
