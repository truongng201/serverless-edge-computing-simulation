// Street Map User Management System
// Handles spawning, movement, and despawning of users on road network

import { 
  getRandomIntersection, 
  findPath, 
  calculateRouteDuration, 
  getRouteWaypoints,
  shouldStopAtTrafficLight 
} from "./road-network";
import { calculateDistance } from "./helper";

// Delete user from backend API
const deleteUserFromBackend = async (userId) => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_user/${userId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        console.log(`Street map user ${userId} deleted from backend`);
      } else {
        console.warn(`Failed to delete user ${userId} from backend:`, response.status);
      }
    }
  } catch (error) {
    console.error(`Error deleting user ${userId} from backend:`, error);
  }
};

// Create user in backend API
export const createUserInBackend = async (user) => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const userData = {
        user_id: user.id,
        location: { x: user.x, y: user.y },
        size: user.size,
        speed: user.baseSpeed
      };
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/create_user_node`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });
      
      if (response.ok) {
        console.log(`Street map user ${user.id} created in backend`);
      } else {
        console.warn(`Failed to create user ${user.id} in backend:`, response.status);
      }
    }
  } catch (error) {
    console.error(`Error creating user ${user.id} in backend:`, error);
  }
};

// Update user position in backend API
const updateUserPositionInBackend = async (user) => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const userData = {
        user_id: user.id,
        location: { x: user.x, y: user.y }
      };
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/update_user_node`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });
      
      if (!response.ok) {
        console.warn(`Failed to update user ${user.id} position in backend:`, response.status);
      }
    }
  } catch (error) {
    console.error(`Error updating user ${user.id} position in backend:`, error);
  }
};

// Generate users for street map scenario
export const generateStreetMapUsers = (roadNetwork, userCount = 50, userSpeed = 30, userSize = 8) => {
  const users = [];
  const { intersections, roads, trafficLights } = roadNetwork;
  
  for (let i = 0; i < userCount; i++) {
    const user = createStreetMapUser(i, intersections, roads, trafficLights, userSpeed, userSize);
    if (user) {
      // Create user in backend API
      createUserInBackend(user);
      users.push(user);
    }
  }
  
  return users;
};

// Create a single street map user with route
export const createStreetMapUser = (id, intersections, roads, trafficLights, userSpeed = 30, userSize = 8) => {
  // Get random start and end intersections
  const startIntersection = getRandomIntersection(intersections);
  const endIntersection = getRandomIntersection(intersections);
  
  // Ensure different start and end points
  if (startIntersection.id === endIntersection.id) {
    return null;
  }
  
  // Find path between intersections
  const path = findPath(startIntersection.id, endIntersection.id, roads, intersections);
  if (!path || path.length < 2) {
    return null;
  }
  
  // Calculate route duration and waypoints
  const routeDuration = calculateRouteDuration(path, roads, intersections, trafficLights);
  const waypoints = getRouteWaypoints(path, intersections);
  
  return {
    id: `street_user_${id}`,
    x: startIntersection.x,
    y: startIntersection.y,
    vx: 0,
    vy: 0,
    type: 'street_map',
    
    // Street map specific properties
    currentIntersection: startIntersection.id,
    targetIntersection: endIntersection.id,
    path: path,
    pathIndex: 0,
    waypoints: waypoints,
    waypointIndex: 0,
    
    // Movement properties
    baseSpeed: userSpeed, // pixels per frame
    currentSpeed: userSpeed,
    size: userSize,
    isMoving: true,
    isWaitingAtLight: false,
    waitingLightId: null,
    
    // Timing properties
    spawnTime: Date.now(),
    routeDuration: routeDuration,
    estimatedArrival: Date.now() + routeDuration,
    
    // Stop detection properties
    lastPosition: { x: startIntersection.x, y: startIntersection.y },
    lastMoveTime: Date.now(),
    stoppedDuration: 0,
    maxStopTime: 5000, // Auto-delete if stopped for 5 seconds
    
    // Serverless function properties
    assignedEdge: null,
    assignedCentral: null,
    assignedNodeID: null,
    latency: 50 + Math.random() * 100,
    last_executed_period: null,
    manualConnection: false,
    
    // Serverless workload properties
    functionType: getRandomFunctionType(),
    resourceRequirements: generateResourceRequirements(),
    requestFrequency: Math.random() * 5 + 1, // 1-6 requests per second
    dataSize: 100 + Math.random() * 400, // 100-500 MB like the latency formula
    priority: Math.floor(Math.random() * 3) + 1, // 1-3 priority levels
    
    // Visual properties
    color: getRandomVehicleColor(),
    direction: 0, // angle in radians
  };
};

// Get random vehicle color
const getRandomVehicleColor = () => {
  const colors = [
    '#3B82F6', // Blue
    '#EF4444', // Red  
    '#10B981', // Green
    '#F59E0B', // Yellow
    '#8B5CF6', // Purple
    '#06B6D4', // Cyan
    '#F97316', // Orange
    '#84CC16', // Lime
  ];
  return colors[Math.floor(Math.random() * colors.length)];
};

// Get random serverless function type for vehicle
const getRandomFunctionType = () => {
  const functionTypes = [
    'video_processing',    // Video streaming/processing
    'image_recognition',   // AI/ML image analysis
    'data_analytics',      // Real-time data processing
    'map_navigation',      // Route calculation
    'traffic_analysis',    // Traffic pattern analysis
    'sensor_processing',   // IoT sensor data
    'communication',       // Vehicle-to-vehicle communication
    'safety_monitoring'    // Real-time safety checks
  ];
  return functionTypes[Math.floor(Math.random() * functionTypes.length)];
};

// Generate resource requirements based on function type
const generateResourceRequirements = () => {
  const requirements = {
    cpu: Math.random() * 2 + 0.5, // 0.5-2.5 CPU cores
    memory: Math.floor(Math.random() * 1024 + 256), // 256-1280 MB
    storage: Math.floor(Math.random() * 512 + 128), // 128-640 MB
    bandwidth: Math.floor(Math.random() * 100 + 10), // 10-110 Mbps
    executionTime: Math.random() * 5000 + 500, // 500-5500 ms
  };
  
  return requirements;
};

// Update street map users movement
export const updateStreetMapUsers = (users, roadNetwork, simulationSpeed = 1) => {
  const { intersections, roads, trafficLights } = roadNetwork;
  const currentTime = Date.now();
  
  // First pass: update users and mark despawn flags
  const updatedUsers = users.map(user => {
    if (user.type !== 'street_map') return user;
    
    // Check if user should despawn (reached destination or timeout)
    if (user.waypointIndex >= user.waypoints.length - 1 || 
        user.pathIndex >= user.path.length - 1 || 
        currentTime > user.estimatedArrival) {
      return { 
        ...user, 
        shouldDespawn: true,
        // Clear assignments immediately so connection lines won't render this frame
        assignedEdge: null,
        assignedCentral: null,
        assignedNodeID: null,
      };
    }

    // Check if user is very close to final destination
    if (user.waypoints && user.waypoints.length > 0) {
      const finalDestination = user.waypoints[user.waypoints.length - 1];
      const distanceToDestination = Math.sqrt(
        Math.pow(user.x - finalDestination.x, 2) + 
        Math.pow(user.y - finalDestination.y, 2)
      );
      if (distanceToDestination < 15) { // Within 15 pixels of destination
        return { 
          ...user, 
          shouldDespawn: true,
          assignedEdge: null,
          assignedCentral: null,
          assignedNodeID: null,
        };
      }
    }

    // Check if user has stopped moving for too long
    const hasMovedSinceLastUpdate = 
      Math.abs(user.x - user.lastPosition.x) > 1 || 
      Math.abs(user.y - user.lastPosition.y) > 1;
    
    let updatedStoppedDuration = user.stoppedDuration;
    let lastMoveTime = user.lastMoveTime;
    
    if (hasMovedSinceLastUpdate) {
      // User is moving, reset stopped duration
      updatedStoppedDuration = 0;
      lastMoveTime = currentTime;
    } else {
      // User hasn't moved, increase stopped duration
      updatedStoppedDuration = currentTime - lastMoveTime;
    }
    
    // Auto-delete if user has been stopped for too long (and not waiting at traffic light)
    if (updatedStoppedDuration > user.maxStopTime && !user.isWaitingAtLight) {
      return { 
        ...user, 
        shouldDespawn: true,
        assignedEdge: null,
        assignedCentral: null,
        assignedNodeID: null,
      };
    }
    
    // Check if waiting at traffic light
    if (user.isWaitingAtLight) {
      const light = trafficLights.find(l => l.id === user.waitingLightId);
      if (light && light.state === 'green') {
        // Can continue moving
        return {
          ...user,
          isWaitingAtLight: false,
          waitingLightId: null,
          isMoving: true,
          currentSpeed: user.baseSpeed,
          lastPosition: { x: user.x, y: user.y },
          lastMoveTime: lastMoveTime,
          stoppedDuration: updatedStoppedDuration
        };
      } else {
        // Still waiting
        return {
          ...user,
          currentSpeed: 0,
          vx: 0,
          vy: 0,
          lastPosition: { x: user.x, y: user.y },
          lastMoveTime: lastMoveTime,
          stoppedDuration: updatedStoppedDuration
        };
      }
    }
    
    // Check if should stop at traffic light
    const nearbyLight = shouldStopAtTrafficLight(
      { x: user.x, y: user.y, vx: user.vx, vy: user.vy }, 
      trafficLights, 
      user.direction, 
      40
    );
    if (nearbyLight) {
      return {
        ...user,
        isWaitingAtLight: true,
        waitingLightId: nearbyLight.id,
        isMoving: false,
        currentSpeed: 0,
        vx: 0,
        vy: 0,
        lastPosition: { x: user.x, y: user.y },
        lastMoveTime: lastMoveTime,
        stoppedDuration: updatedStoppedDuration
      };
    }
    
    // Normal movement along path
    if (user.waypointIndex < user.waypoints.length - 1) {
      const currentWaypoint = user.waypoints[user.waypointIndex];
      const nextWaypoint = user.waypoints[user.waypointIndex + 1];
      
      // Calculate direction to next waypoint
      const dx = nextWaypoint.x - user.x;
      const dy = nextWaypoint.y - user.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      if (distance < 10) {
        // Reached current waypoint, move to next
        return {
          ...user,
          waypointIndex: user.waypointIndex + 1,
          pathIndex: user.waypointIndex + 1,
          currentIntersection: user.path[user.waypointIndex + 1] || user.currentIntersection,
          lastPosition: { x: user.x, y: user.y },
          lastMoveTime: lastMoveTime,
          stoppedDuration: updatedStoppedDuration
        };
      }
      
      // Move towards next waypoint
      const normalizedDx = dx / distance;
      const normalizedDy = dy / distance;
      const speed = user.currentSpeed * simulationSpeed;
      
      return {
        ...user,
        x: user.x + normalizedDx * speed,
        y: user.y + normalizedDy * speed,
        vx: normalizedDx * speed,
        vy: normalizedDy * speed,
        direction: Math.atan2(dy, dx),
        lastPosition: { x: user.x, y: user.y },
        lastMoveTime: lastMoveTime,
        stoppedDuration: updatedStoppedDuration
      };
    }
    
    return {
      ...user,
      lastPosition: { x: user.x, y: user.y },
      lastMoveTime: lastMoveTime,
      stoppedDuration: updatedStoppedDuration
    };
  });
  
  // Handle user despawning and API cleanup
  const usersToKeep = [];
  const usersToDelete = [];
  
  updatedUsers.forEach(user => {
    if (user.type === 'street_map' && user.shouldDespawn) {
      usersToDelete.push(user);
    } else {
      usersToKeep.push(user);
    }
  });
  
  // Delete users from backend API if they should despawn
  usersToDelete.forEach(user => {
    try {
      console.log(`Despawning user ${user.id}: reached destination or timeout`);
      deleteUserFromBackend(user.id);
    } catch (e) {
      console.warn('Failed to delete user from backend', user.id, e);
    }
  });
  
  // Update user positions in backend periodically (every few updates to avoid spamming)
  if (Math.random() > 0.9) { // 10% chance to update positions
    usersToKeep.forEach(user => {
      if (user.type === 'street_map') {
        updateUserPositionInBackend(user);
      }
    });
  }
  
  return usersToKeep;
};

// Spawn new users periodically
export const spawnNewStreetMapUsers = (
  currentUsers, 
  roadNetwork, 
  maxUsers = 100, 
  spawnRate = 0.1, // probability per frame
  userSpeed = 30, 
  userSize = 8
) => {
  const { intersections, roads, trafficLights } = roadNetwork;
  const streetMapUsers = currentUsers.filter(u => u.type === 'street_map');
  
  // Don't spawn if at max capacity
  if (streetMapUsers.length >= maxUsers) {
    return currentUsers;
  }
  
  // Random chance to spawn new user
  if (Math.random() > spawnRate) {
    return currentUsers;
  }
  
  // Create new user
  const newUserId = Date.now() + Math.random() * 1000;
  const newUser = createStreetMapUser(newUserId, intersections, roads, trafficLights, userSpeed, userSize);
  
  if (newUser) {
    // Create user in backend API
    createUserInBackend(newUser);
    return [...currentUsers, newUser];
  }
  
  return currentUsers;
};

// Real-time spawn: spawn users based on time interval rather than per-frame probability
// Returns { users, lastSpawnAt }
export const spawnStreetUsersByTime = (
  currentUsers,
  roadNetwork,
  maxUsers = 100,
  spawnPerSecond = 1,
  userSpeed = 30,
  userSize = 8,
  now = Date.now(),
  lastSpawnAt = null,
  maxPerTick = 3
) => {
  const { intersections, roads, trafficLights } = roadNetwork;
  const streetMapUsers = currentUsers.filter(u => u.type === 'street_map');
  let users = currentUsers;

  if (streetMapUsers.length >= maxUsers) {
    return { users, lastSpawnAt: lastSpawnAt ?? now };
  }

  // If spawn rate is zero or negative, do nothing
  if (!spawnPerSecond || spawnPerSecond <= 0) {
    return { users, lastSpawnAt: lastSpawnAt ?? now };
  }

  const intervalMs = 1000 / spawnPerSecond;
  let nextSpawnTime = lastSpawnAt ?? now;
  let spawnedThisTick = 0;

  while (now - nextSpawnTime >= intervalMs && users.filter(u => u.type === 'street_map').length < maxUsers) {
    // Create new user
    const newUserId = Date.now() + Math.random() * 1000;
    const newUser = createStreetMapUser(newUserId, intersections, roads, trafficLights, userSpeed, userSize);
    if (newUser) {
      // Register in backend (fire and forget)
      createUserInBackend(newUser);
      users = [...users, newUser];
      spawnedThisTick++;
    }
    nextSpawnTime += intervalMs;

    if (spawnedThisTick >= maxPerTick) break; // safety cap per tick
  }

  // Ensure lastSpawnAt never jumps backwards
  const updatedLastSpawnAt = nextSpawnTime > now ? nextSpawnTime - intervalMs : nextSpawnTime;
  return { users, lastSpawnAt: updatedLastSpawnAt };
};

// Convert regular users to street map users
export const convertToStreetMapUsers = (users, roadNetwork, userSpeed = 30) => {
  const { intersections, roads, trafficLights } = roadNetwork;
  
  return users.map((user, index) => {
    // Keep non-street-map users as is
    if (user.type && user.type !== 'street_map') {
      return user;
    }
    
    // Find nearest intersection to current user position
    let nearestIntersection = intersections[0];
    let minDistance = calculateDistance(user.x, user.y, intersections[0].x, intersections[0].y);
    
    intersections.forEach(intersection => {
      const distance = calculateDistance(user.x, user.y, intersection.x, intersection.y);
      if (distance < minDistance) {
        minDistance = distance;
        nearestIntersection = intersection;
      }
    });
    
    // Create street map user starting from nearest intersection
    const streetUser = createStreetMapUser(
      user.id || index, 
      intersections, 
      roads, 
      trafficLights, 
      userSpeed, 
      user.size || 8
    );
    
    if (streetUser) {
      // Preserve some original properties
      return {
        ...streetUser,
        id: user.id || streetUser.id,
        assignedEdge: user.assignedEdge || null,
        assignedCentral: user.assignedCentral || null,
        assignedNodeID: user.assignedNodeID || null,
        latency: user.latency || streetUser.latency,
      };
    }
    
    return user; // Fallback to original user if conversion fails
  });
};

// Simulate serverless function execution for street map users
export const simulateServerlessFunctions = (users, edgeNodes, centralNodes) => {
  return users.map(user => {
    if (user.type !== 'street_map') return user;
    
    // Simulate function execution only if user has assigned node and is moving
    if ((user.assignedEdge || user.assignedCentral) && user.isMoving) {
      const currentTime = Date.now();
      const timeSinceLastExecution = currentTime - (user.last_executed_period || 0);
      const executionInterval = 1000 / user.requestFrequency; // Convert frequency to interval
      
      // Execute function if enough time has passed
      if (timeSinceLastExecution >= executionInterval) {
        // Find assigned node
        let assignedNode = null;
        if (user.assignedEdge) {
          assignedNode = edgeNodes.find(node => node.id === user.assignedEdge);
        } else if (user.assignedCentral) {
          assignedNode = centralNodes.find(node => node.id === user.assignedCentral);
        }
        
        if (assignedNode) {
          // Simulate function execution latency
          const baseLatency = user.latency || 100;
          const executionLatency = user.resourceRequirements.executionTime + (Math.random() * 50);
          const totalLatency = baseLatency + executionLatency;
          
          // Update node load (simulate resource consumption)
          assignedNode.currentLoad = Math.min(100, assignedNode.currentLoad + user.resourceRequirements.cpu * 5);
          
          return {
            ...user,
            last_executed_period: currentTime,
            latency: totalLatency,
            lastExecutionResult: {
              timestamp: currentTime,
              executionTime: executionLatency,
              success: Math.random() > 0.05, // 95% success rate
              resourcesUsed: user.resourceRequirements
            }
          };
        }
      }
    }
    
    return user;
  });
};

// Auto-assign street map users to available nodes
export const autoAssignStreetMapUsers = (users, edgeNodes, centralNodes, assignmentAlgorithm = 'nearest-distance') => {
  return users.map(user => {
    if (user.type !== 'street_map' || user.assignedEdge || user.assignedCentral) {
      return user; // Skip if not street map user or already assigned
    }
    
    let bestNode = null;
    let bestType = null;
    let bestLatency = Number.POSITIVE_INFINITY;
    
    const allNodes = [
      ...edgeNodes.map(node => ({ ...node, nodeType: 'edge' })),
      ...centralNodes.map(node => ({ ...node, nodeType: 'central' }))
    ];
    
    // Find best node based on assignment algorithm
    allNodes.forEach(node => {
      let score = 0;
      
      switch (assignmentAlgorithm) {
        case 'nearest-distance':
          const distance = calculateDistance(user.x, user.y, node.x, node.y);
          score = distance;
          break;
        case 'load-aware':
          const distance2 = calculateDistance(user.x, user.y, node.x, node.y);
          const loadFactor = (node.currentLoad || 0) / 100;
          score = distance2 * (1 + loadFactor);
          break;
        case 'resource-aware':
          const distance3 = calculateDistance(user.x, user.y, node.x, node.y);
          const resourceFit = Math.abs((node.coverage || 100) - user.resourceRequirements.cpu * 20);
          score = distance3 + resourceFit;
          break;
        default:
          score = Math.random() * 1000;
      }
      
      if (score < bestLatency) {
        bestLatency = score;
        bestNode = node;
        bestType = node.nodeType;
      }
    });
    
    if (bestNode) {
      return {
        ...user,
        assignedEdge: bestType === 'edge' ? bestNode.id : null,
        assignedCentral: bestType === 'central' ? bestNode.id : null,
        assignedNodeID: bestNode.id,
        latency: bestLatency + user.resourceRequirements.executionTime / 10,
        manualConnection: false
      };
    }
    
    return user;
  });
};

// Get street map simulation statistics
export const getStreetMapStats = (users, roadNetwork) => {
  const streetMapUsers = users.filter(u => u.type === 'street_map');
  const waitingAtLights = streetMapUsers.filter(u => u.isWaitingAtLight).length;
  const moving = streetMapUsers.filter(u => u.isMoving).length;
  const assigned = streetMapUsers.filter(u => u.assignedEdge || u.assignedCentral).length;
  const executing = streetMapUsers.filter(u => u.lastExecutionResult?.timestamp > Date.now() - 5000).length;
  
  const totalRouteDistance = streetMapUsers.reduce((sum, user) => {
    if (user.waypoints && user.waypoints.length > 1) {
      let distance = 0;
      for (let i = 0; i < user.waypoints.length - 1; i++) {
        distance += calculateDistance(
          user.waypoints[i].x, 
          user.waypoints[i].y,
          user.waypoints[i + 1].x, 
          user.waypoints[i + 1].y
        );
      }
      return sum + distance;
    }
    return sum;
  }, 0);
  
  // Group by function type
  const functionTypes = streetMapUsers.reduce((acc, user) => {
    const type = user.functionType || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {});
  
  return {
    totalUsers: streetMapUsers.length,
    movingUsers: moving,
    waitingAtLights: waitingAtLights,
    assignedUsers: assigned,
    executingFunctions: executing,
    averageRouteDistance: streetMapUsers.length > 0 ? totalRouteDistance / streetMapUsers.length : 0,
    averageLatency: streetMapUsers.length > 0 ? streetMapUsers.reduce((sum, u) => sum + (u.latency || 0), 0) / streetMapUsers.length : 0,
    functionTypes: functionTypes,
    totalIntersections: roadNetwork.intersections.length,
    totalRoads: roadNetwork.roads.length,
    activeTrafficLights: roadNetwork.trafficLights.filter(l => l.state !== 'green').length
  };
};
