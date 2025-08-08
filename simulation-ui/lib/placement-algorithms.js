import { calculateDistance } from "./road-utils";

// Auto Placement Algorithms
export const topKDemandPlacement = (users, candidates, k, lMax) => {
  // Calculate demand score for each candidate
  const candidateScores = candidates.map((candidate) => {
    const score = users.reduce((total, user) => {
      const distance = calculateDistance(user.x, user.y, candidate.x, candidate.y);
      return distance <= lMax ? total + 1 : total; // weight = 1 for all users
    }, 0);
    return { ...candidate, score };
  });

  // Sort by score descending and take top K
  candidateScores.sort((a, b) => b.score - a.score);
  return candidateScores.slice(0, k);
};

export const kMeansPlacement = (users, candidates, k) => {
  if (users.length === 0) return [];
  
  // Simple K-means implementation
  // Initialize centroids randomly from users
  let centroids = [];
  const shuffledUsers = [...users].sort(() => Math.random() - 0.5);
  for (let i = 0; i < Math.min(k, shuffledUsers.length); i++) {
    centroids.push({ x: shuffledUsers[i].x, y: shuffledUsers[i].y });
  }

  // K-means iterations
  for (let iter = 0; iter < 10; iter++) {
    // Assign users to nearest centroid
    const clusters = Array(k).fill().map(() => []);
    users.forEach(user => {
      let minDist = Infinity;
      let assignedCluster = 0;
      centroids.forEach((centroid, idx) => {
        const dist = calculateDistance(user.x, user.y, centroid.x, centroid.y);
        if (dist < minDist) {
          minDist = dist;
          assignedCluster = idx;
        }
      });
      clusters[assignedCluster].push(user);
    });

    // Update centroids
    const newCentroids = clusters.map(cluster => {
      if (cluster.length === 0) return centroids[0]; // Handle empty cluster
      const avgX = cluster.reduce((sum, user) => sum + user.x, 0) / cluster.length;
      const avgY = cluster.reduce((sum, user) => sum + user.y, 0) / cluster.length;
      return { x: avgX, y: avgY };
    });

    centroids = newCentroids;
  }

  // Find nearest candidate for each centroid
  return centroids.map(centroid => {
    let nearestCandidate = candidates[0];
    let minDist = calculateDistance(centroid.x, centroid.y, candidates[0].x, candidates[0].y);
    
    candidates.forEach(candidate => {
      const dist = calculateDistance(centroid.x, centroid.y, candidate.x, candidate.y);
      if (dist < minDist) {
        minDist = dist;
        nearestCandidate = candidate;
      }
    });
    
    return nearestCandidate;
  });
};

export const randomRandomPlacement = (users, candidates, k) => {
  // Random K candidates
  const shuffledCandidates = [...candidates].sort(() => Math.random() - 0.5);
  return shuffledCandidates.slice(0, k);
};

export const randomNearestPlacement = (users, candidates, k) => {
  // Same as random-random for placement, difference is in assignment
  return randomRandomPlacement(users, candidates, k);
};

// Calculate latency based on connection using experimental formula
export const calculateLatency = (user, nodeId, nodeType, edgeNodes, centralNodes) => {
  let targetNode = null;
  if (nodeType === "edge") {
    targetNode = edgeNodes.find((edge) => edge.id === nodeId);
  } else if (nodeType === "central") {
    targetNode = centralNodes.find((central) => central.id === nodeId);
  }

  if (!targetNode) return 100 + Math.random() * 50;

  // Generate random data size s(u,t) in range [100, 500] MB
  const dataSize = 100 + Math.random() * 400; // MB
  
  // Determine if it's Cold Start or Warm Start
  const isWarmStart = targetNode.isWarm || false; // I_{u,v,t}
  const coldStartIndicator = isWarmStart ? 1 : 0;
  
  // Calculate Communication Delay: d_com = s(u,t) × τ(v_u,t, v)
  let unitTransmissionDelay; // τ (ms/MB)
  if (nodeType === "edge") {
    // Between APs: [0.2, 1] ms/MB
    unitTransmissionDelay = 0.2 + Math.random() * 0.8;
  } else {
    // To Cloud: [2, 10] ms/MB  
    unitTransmissionDelay = 2 + Math.random() * 8;
  }
  const communicationDelay = dataSize * unitTransmissionDelay;
  
  // Calculate Processing Delay: d_proc = (1 - I_{u,v,t}) × d_cold + s(u,t) × ρ_{u,v}
  
  // Cold start delay [100, 500] ms
  const coldStartDelay = 100 + Math.random() * 400;
  
  // Unit processing time ρ_{u,v} (ms/MB)
  let unitProcessingTime;
  if (nodeType === "edge") {
    // Cloudlet: [0.5, 2] ms/MB
    unitProcessingTime = 0.5 + Math.random() * 1.5;
  } else {
    // Cloud: 0.05 ms/MB
    unitProcessingTime = 0.05;
  }
  
  const processingDelay = (1 - coldStartIndicator) * coldStartDelay + dataSize * unitProcessingTime;
  
  // Total Service Delay: D(u,v,t) = d_com + d_proc
  const totalLatency = communicationDelay + processingDelay;
  
  // Mark node as warm for next requests (simulating container reuse)
  if (targetNode) {
    targetNode.isWarm = true;
    targetNode.lastAccessTime = Date.now();
  }
  
  // Store additional metrics for debugging/display
  if (targetNode) {
    targetNode.lastMetrics = {
      dataSize: Math.round(dataSize),
      communicationDelay: Math.round(communicationDelay),
      processingDelay: Math.round(processingDelay),
      isWarmStart: isWarmStart,
      unitTransmissionDelay: unitTransmissionDelay.toFixed(3),
      unitProcessingTime: unitProcessingTime.toFixed(3)
    };
  }
  
  return Math.round(totalLatency);
};
