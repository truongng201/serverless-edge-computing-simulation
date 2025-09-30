export function calculateDistance(point1X, point1Y, point2X, point2Y) {
  const dx = point2X - point1X;
  const dy = point2Y - point1Y;
  return Math.sqrt(dx * dx + dy * dy);
}

export function calculateLatency(currNode, targetNodeId, allNodes) {
  if (!currNode || !targetNodeId || !allNodes) {
    return 100 + Math.random() * 50; // Default latency if parameters are missing from 100 to 150 ms
  }

  let tagetNode = null;
  for (let i = 0; i < allNodes.length; i++) {
    if (allNodes[i].id === targetNodeId) {
      tagetNode = allNodes[i];
      break;
    }
  }
  if (!tagetNode) {
    return 100 + Math.random() * 50; // Default latency if target node not found
  }
  const distance = calculateDistance(
    currNode.x,
    currNode.y,
    tagetNode.x,
    tagetNode.y
  );
  // latency = distance * 0.3 + random factor (0 to 15 ms)
  const latency = distance * 0.3 + Math.random() * 15;
  return Math.round(latency);
}

export const formatNumber = (num) => {
  if (num === 0) return "0";
  if (num < 1) return num.toFixed(3);
  if (num < 100) return num.toFixed(2);
  return Math.round(num).toLocaleString();
};

export const formatMs = (ms) => {
  if (ms < 1000) return `${formatNumber(ms)}ms`;
  return `${formatNumber(ms / 1000)}s`;
};

export default {
  calculateDistance,
  formatNumber,
  formatMs,
};
