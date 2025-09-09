import useGlobalState from "@/hooks/use-global-state";
import { 
  topKDemandPlacement, 
  kMeansPlacement, 
  randomRandomPlacement, 
  randomNearestPlacement,
  calculateLatency 
} from "./placement-algorithms";
import { calculateDistance } from "../helper";

export const runPlacementAlgorithm = () => {
  const { users, edgeNodes, placementAlgorithm, setEdgeNodes, setUsers } =
    useGlobalState.getState();
  if (users.length === 0) {
    return;
  }

  const k = edgeNodes.length;
  if (k === 0) {
    return;
  }

  // Use user positions as candidates
  const candidates = users.map((user) => ({ x: user.x, y: user.y }));
  let selectedPositions = [];
  const maxCoverageDistance = 300;
  switch (placementAlgorithm) {
    case "topk-demand":
      selectedPositions = topKDemandPlacement(
        users,
        candidates,
        k,
        maxCoverageDistance
      );
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
      return;
  }

  // Update edge node positions
  setEdgeNodes((prevNodes) => {
    return prevNodes.map((node, index) => {
      if (index < selectedPositions.length) {
        return {
          ...node,
          x: selectedPositions[index].x,
          y: selectedPositions[index].y,
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
        y: selectedPositions[index].y,
      };
    }
    return node;
  });

  setUsers((prevUsers) => {
    return prevUsers.map((user) => {
      if (placementAlgorithm === "random-random") {
        // Random assignment for random-random
        const randomNode =
          updatedNodes[Math.floor(Math.random() * updatedNodes.length)];
        return {
          ...user,
          assignedEdge: randomNode.id,
          assignedCentral: null,
          manualConnection: false,
          latency: calculateLatency(
            user,
            randomNode.id,
            "edge",
            updatedNodes,
            []
          ),
        };
      } else {
        // Nearest assignment for other algorithms
        let nearestNode = updatedNodes[0];
        let minDist = calculateDistance(
          user.x,
          user.y,
          updatedNodes[0].x,
          updatedNodes[0].y
        );

        updatedNodes.forEach((node) => {
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
          latency: calculateLatency(
            user,
            nearestNode.id,
            "edge",
            updatedNodes,
            []
          ),
        };
      }
    });
  });
};
