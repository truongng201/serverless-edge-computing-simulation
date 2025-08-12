import { 
  topKDemandPlacement, 
  kMeansPlacement, 
  randomRandomPlacement, 
  randomNearestPlacement,
  calculateLatency 
} from "./placement-algorithms";
import { calculateDistance } from "./helper";

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
    alert("No users available for placement algorithm");
    return;
  }

  const k = edgeNodes.length;
  if (k === 0) {
    alert("No edge nodes available for placement");
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

// Manually connect user to a specific node
export const connectUserToNode = (userId, nodeId, nodeType, setUsers, edgeNodes, centralNodes) => {
  setUsers((prevUsers) =>
    prevUsers.map((user) => {
      if (user.id === userId) {
        const latency = calculateLatency(user, nodeId, nodeType, edgeNodes, centralNodes);
        return {
          ...user,
          assignedEdge: nodeType === "edge" ? nodeId : null,
          assignedCentral: nodeType === "central" ? nodeId : null,
          manualConnection: true,
          latency,
        };
      }
      return user;
    })
  );
};

// Disconnect user from all nodes
export const disconnectUser = (userId, setUsers) => {
  setUsers((prevUsers) => {
    const newUsers = [];
    for (let i = 0; i < prevUsers.length; i++) {
      const user = prevUsers[i];
      if (user.id === userId) {
        newUsers.push({
          ...user,
          assignedEdge: null,
          assignedCentral: null,
          manualConnection: false,
          latency: 100 + Math.random() * 50,
        });
      } else {
        newUsers.push(user);
      }
    }
    return newUsers;
  });
};

// Reset all manual connections
export const resetAllConnections = (setUsers) => {
  setUsers((prevUsers) => {
    const newUsers = [];
    for (let i = 0; i < prevUsers.length; i++) {
      newUsers.push({ ...prevUsers[i], manualConnection: false });
    }
    return newUsers;
  });
};

// Update selected user properties
export const updateSelectedUser = (selectedUser, updates, setUsers, setSelectedUser) => {
  if (!selectedUser) return;
  setUsers((prevUsers) => {
    const newUsers = [];
    for (let i = 0; i < prevUsers.length; i++) {
      const user = prevUsers[i];
      if (user.id === selectedUser.id) {
        newUsers.push({ ...user, ...updates });
      } else {
        newUsers.push(user);
      }
    }
    return newUsers;
  });
  setSelectedUser((prev) => ({ ...prev, ...updates }));
};

// Delete selected user
export const deleteSelectedUser = (selectedUser, setUsers, setSelectedUser) => {
  if (!selectedUser) return;
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
