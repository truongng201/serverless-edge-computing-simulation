/**
 * GAP (Generalized Assignment Problem) Solver for User Assignment
 * 
 * Implements the baseline algorithm from the paper, but uses existing
 * calculateLatency function instead of implementing new latency calculation.
 */

import { calculateLatency } from "./placement-algorithms";

/**
 * Build profit matrix H[u][v] = utility gain when assigning user u to node v
 * H[u][v] = D(u, cloud, t) - D(u, v, t) 
 * where D = latency (using existing calculateLatency function)
 */
function buildProfitMatrix(users, edgeNodes, centralNodes, latencyParams) {
  const profits = {};
  
  // Create a virtual cloud node for comparison
  const cloudNode = { id: 'cloud', x: 0, y: 0, type: 'cloud' };
  
  users.forEach(user => {
    profits[user.id] = {};
    
    // Calculate cloud latency (baseline for comparison)
    const cloudLatency = calculateLatency(user, cloudNode.id, "central", edgeNodes, [cloudNode], latencyParams);
    
    // Calculate profit for each edge node
    edgeNodes.forEach(node => {
      const nodeLatency = calculateLatency(user, node.id, "edge", edgeNodes, centralNodes, latencyParams);
      profits[user.id][node.id] = Math.max(0, cloudLatency - nodeLatency); // Utility gain
    });
    
    // Calculate profit for each central node  
    centralNodes.forEach(node => {
      const nodeLatency = calculateLatency(user, node.id, "central", edgeNodes, centralNodes, latencyParams);
      profits[user.id][node.id] = Math.max(0, cloudLatency - nodeLatency); // Utility gain
    });
    
    // Cloud has 0 profit (baseline)
    profits[user.id]['cloud'] = 0;
  });
  
  return profits;
}

/**
 * Simple greedy approximation for GAP
 * Since we don't have memory constraints in the current system,
 * this becomes a maximum weight bipartite matching problem
 */
function solveGAPGreedy(users, edgeNodes, centralNodes, latencyParams) {
  const profits = buildProfitMatrix(users, edgeNodes, centralNodes, latencyParams);
  const assignment = {};
  
  // Create list of all nodes (edge + central + cloud)
  const allNodes = [
    ...edgeNodes.map(n => ({...n, type: 'edge'})),
    ...centralNodes.map(n => ({...n, type: 'central'})),
    { id: 'cloud', type: 'cloud', x: 0, y: 0 }
  ];
  
  // For each user, find the node with maximum profit
  users.forEach(user => {
    let bestNode = null;
    let bestProfit = -1;
    
    allNodes.forEach(node => {
      const profit = profits[user.id][node.id] || 0;
      if (profit > bestProfit) {
        bestProfit = profit;
        bestNode = node;
      }
    });
    
    if (bestNode) {
      assignment[user.id] = {
        nodeId: bestNode.id,
        nodeType: bestNode.type === 'cloud' ? 'central' : bestNode.type,
        profit: bestProfit,
        latency: bestNode.type === 'cloud' 
          ? calculateLatency(user, 'cloud', "central", edgeNodes, [{ id: 'cloud', x: 0, y: 0 }], latencyParams)
          : calculateLatency(user, bestNode.id, bestNode.type, edgeNodes, centralNodes, latencyParams)
      };
    }
  });
  
  return assignment;
}

/**
 * ILP solver using simple optimization (placeholder for OR-Tools integration)
 * For now, falls back to greedy since we don't have memory constraints
 */
function solveGAPILP(users, edgeNodes, centralNodes, latencyParams) {
  // TODO: Implement actual ILP solver when memory constraints are added
  // For now, use greedy approximation
  console.log("ILP solver not implemented, using greedy approximation");
  return solveGAPGreedy(users, edgeNodes, centralNodes, latencyParams);
}

/**
 * Main GAP solver entry point
 * @param {Array} users - List of users to assign
 * @param {Array} edgeNodes - Available edge nodes
 * @param {Array} centralNodes - Available central nodes  
 * @param {Object} options - Solver options
 * @returns {Object} Assignment mapping user.id -> {nodeId, nodeType, profit, latency}
 */
export function solveGAP(users, edgeNodes, centralNodes, options = {}) {
  const {
    method = 'greedy', // 'greedy' or 'ilp'
    latencyParams = null,
    enableMemoryConstraints = false
  } = options;
  
  if (users.length === 0) {
    return {};
  }
  
  if (edgeNodes.length === 0 && centralNodes.length === 0) {
    console.warn("No nodes available for GAP assignment");
    return {};
  }
  
  try {
    switch (method) {
      case 'ilp':
        return solveGAPILP(users, edgeNodes, centralNodes, latencyParams);
      case 'greedy':
      default:
        return solveGAPGreedy(users, edgeNodes, centralNodes, latencyParams);
    }
  } catch (error) {
    console.error("GAP solver error:", error);
    // Fallback to simple nearest assignment
    const fallbackAssignment = {};
    users.forEach(user => {
      if (edgeNodes.length > 0) {
        const nearestEdge = edgeNodes[0]; // Simple fallback
        fallbackAssignment[user.id] = {
          nodeId: nearestEdge.id,
          nodeType: 'edge',
          profit: 0,
          latency: calculateLatency(user, nearestEdge.id, 'edge', edgeNodes, centralNodes, latencyParams)
        };
      }
    });
    return fallbackAssignment;
  }
}

/**
 * Utility function to get assignment statistics
 */
export function getGAPStats(assignment, users) {
  const stats = {
    totalUsers: users.length,
    assignedUsers: Object.keys(assignment).length,
    totalUtility: 0,
    avgLatency: 0,
    edgeAssignments: 0,
    centralAssignments: 0,
    cloudAssignments: 0
  };
  
  let totalLatency = 0;
  
  Object.values(assignment).forEach(assign => {
    stats.totalUtility += assign.profit || 0;
    totalLatency += assign.latency || 0;
    
    if (assign.nodeType === 'edge') stats.edgeAssignments++;
    else if (assign.nodeType === 'central') stats.centralAssignments++;
    else stats.cloudAssignments++;
  });
  
  stats.avgLatency = stats.assignedUsers > 0 ? totalLatency / stats.assignedUsers : 0;
  
  return stats;
}
