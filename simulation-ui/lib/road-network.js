// Road Network System for Saigon Street Simulation
// Handles roads, intersections, traffic lights, and pathfinding

import { calculateDistance } from "./helper";

// Generate Saigon-style road network for 3km x 3km area
export const generateSaigonRoadNetwork = (width = 3000, height = 3000) => {
  const intersections = [];
  const roads = [];
  const trafficLights = [];
  
  // Main street configuration (simulating major Saigon streets)
  const mainStreets = [
    // Horizontal major streets (like Lê Lợi, Đồng Khởi) - reduced to 3 main streets
    { y: height * 0.25, name: "Le Loi Street" },
    { y: height * 0.5, name: "Dong Khoi Street" },
    { y: height * 0.75, name: "Nguyen Hue Street" },
  ];
  
  // Vertical major streets (like Nguyễn Huệ, Nam Kỳ Khởi Nghĩa) - reduced to 3 main streets
  const verticalStreets = [
    { x: width * 0.25, name: "Nguyen Hue Blvd" },
    { x: width * 0.5, name: "Nam Ky Khoi Nghia" },
    { x: width * 0.75, name: "Le Duan Street" },
  ];
  
  // Secondary roads (connecting roads only) - more strategic placement
  const secondaryHorizontal = [
    { y: height * 0.125 }, // Between top and first main
    { y: height * 0.375 }, // Between first and second main  
    { y: height * 0.625 }, // Between second and third main
    { y: height * 0.875 }, // Between third main and bottom
  ];
  
  const secondaryVertical = [
    { x: width * 0.125 }, // Between left and first main
    { x: width * 0.375 }, // Between first and second main
    { x: width * 0.625 }, // Between second and third main
    { x: width * 0.875 }, // Between third main and right
  ];

  // Generate intersections at crossings
  let intersectionId = 0;
  
  // Main street intersections
  mainStreets.forEach(hStreet => {
    verticalStreets.forEach(vStreet => {
      intersections.push({
        id: `intersection_${intersectionId++}`,
        x: vStreet.x,
        y: hStreet.y,
        type: 'major',
        hasTrafficLight: true,
        name: `${hStreet.name} & ${vStreet.name}`
      });
    });
  });
  
  // Secondary intersections
  [...secondaryHorizontal, ...mainStreets].forEach(hStreet => {
    [...secondaryVertical, ...verticalStreets].forEach(vStreet => {
      // Skip if already exists (for main streets)
      const exists = intersections.some(int => 
        Math.abs(int.x - vStreet.x) < 10 && Math.abs(int.y - hStreet.y) < 10
      );
      if (!exists) {
        intersections.push({
          id: `intersection_${intersectionId++}`,
          x: vStreet.x,
          y: hStreet.y,
          type: 'secondary',
          hasTrafficLight: Math.random() > 0.6, // 40% chance for traffic lights
          name: `Intersection ${intersectionId}`
        });
      }
    });
  });

  // Generate roads connecting intersections - only necessary connections
  let roadId = 0;
  
  // Create roads for main street grid (horizontal + vertical main streets)
  const createMainRoads = () => {
    // Horizontal main roads
    mainStreets.forEach(hStreet => {
      const intersectionsOnStreet = intersections.filter(int => Math.abs(int.y - hStreet.y) < 10);
      intersectionsOnStreet.sort((a, b) => a.x - b.x);
      
      for (let i = 0; i < intersectionsOnStreet.length - 1; i++) {
        const from = intersectionsOnStreet[i];
        const to = intersectionsOnStreet[i + 1];
        const distance = calculateDistance(from.x, from.y, to.x, to.y);
        
        roads.push({
          id: `road_${roadId++}`,
          from: from.id,
          to: to.id,
          distance: distance,
          type: 'major',
          speedLimit: 50,
          lanes: 4,
          direction: 'bidirectional',
          waypoints: [
            { x: from.x, y: from.y },
            { x: to.x, y: to.y }
          ]
        });
      }
    });
    
    // Vertical main roads
    verticalStreets.forEach(vStreet => {
      const intersectionsOnStreet = intersections.filter(int => Math.abs(int.x - vStreet.x) < 10);
      intersectionsOnStreet.sort((a, b) => a.y - b.y);
      
      for (let i = 0; i < intersectionsOnStreet.length - 1; i++) {
        const from = intersectionsOnStreet[i];
        const to = intersectionsOnStreet[i + 1];
        const distance = calculateDistance(from.x, from.y, to.x, to.y);
        
        roads.push({
          id: `road_${roadId++}`,
          from: from.id,
          to: to.id,
          distance: distance,
          type: 'major',
          speedLimit: 50,
          lanes: 4,
          direction: 'bidirectional',
          waypoints: [
            { x: from.x, y: from.y },
            { x: to.x, y: to.y }
          ]
        });
      }
    });
  };
  
  // Create secondary roads (connecting roads only)
  const createSecondaryRoads = () => {
    // Horizontal secondary roads
    secondaryHorizontal.forEach(hStreet => {
      const intersectionsOnStreet = intersections.filter(int => Math.abs(int.y - hStreet.y) < 10);
      intersectionsOnStreet.sort((a, b) => a.x - b.x);
      
      for (let i = 0; i < intersectionsOnStreet.length - 1; i++) {
        const from = intersectionsOnStreet[i];
        const to = intersectionsOnStreet[i + 1];
        const distance = calculateDistance(from.x, from.y, to.x, to.y);
        
        roads.push({
          id: `road_${roadId++}`,
          from: from.id,
          to: to.id,
          distance: distance,
          type: 'secondary',
          speedLimit: 30,
          lanes: 2,
          direction: 'bidirectional',
          waypoints: [
            { x: from.x, y: from.y },
            { x: to.x, y: to.y }
          ]
        });
      }
    });
    
    // Vertical secondary roads  
    secondaryVertical.forEach(vStreet => {
      const intersectionsOnStreet = intersections.filter(int => Math.abs(int.x - vStreet.x) < 10);
      intersectionsOnStreet.sort((a, b) => a.y - b.y);
      
      for (let i = 0; i < intersectionsOnStreet.length - 1; i++) {
        const from = intersectionsOnStreet[i];
        const to = intersectionsOnStreet[i + 1];
        const distance = calculateDistance(from.x, from.y, to.x, to.y);
        
        roads.push({
          id: `road_${roadId++}`,
          from: from.id,
          to: to.id,
          distance: distance,
          type: 'secondary',
          speedLimit: 30,
          lanes: 2,
          direction: 'bidirectional',
          waypoints: [
            { x: from.x, y: from.y },
            { x: to.x, y: to.y }
          ]
        });
      }
    });
  };
  
  createMainRoads();
  createSecondaryRoads();

  // Generate traffic lights only at major intersections
  let trafficLightId = 0;
  intersections.forEach(intersection => {
    if (intersection.hasTrafficLight && intersection.type === 'major') {
      // Random initial state for variety
      const states = ['green', 'yellow', 'red'];
      const initialState = states[Math.floor(Math.random() * states.length)];
      
      trafficLights.push({
        id: `traffic_light_${trafficLightId++}`,
        intersectionId: intersection.id,
        x: intersection.x,
        y: intersection.y,
        state: initialState,
        cycleTime: 20000, // 20 seconds total cycle
        greenTime: 10000, // 10 seconds green (5s each direction)
        yellowTime: 2000,  // 2 seconds yellow
        redTime: 8000,     // 8 seconds red (short clearance)
        lastStateChange: Date.now() - Math.random() * 20000, // Random start time in cycle
        directions: ['north-south', 'east-west'], // which directions are controlled
        currentDirection: Math.random() > 0.5 ? 'north-south' : 'east-west' // which direction is currently green
      });
    }
  });

  return {
    intersections,
    roads,
    trafficLights,
    width,
    height
  };
};

// Update traffic light states based on time with proper coordination
export const updateTrafficLights = (trafficLights) => {
  const currentTime = Date.now();
  
  return trafficLights.map((light, index) => {
    const timeSinceChange = currentTime - light.lastStateChange;
    let newState = light.state;
    let newLastStateChange = light.lastStateChange;
    let newCurrentDirection = light.currentDirection;
    
    // Traffic light cycle: North-South green -> Yellow -> Red -> East-West green -> Yellow -> Red
    const totalCycleTime = light.greenTime + light.yellowTime + light.redTime;
    const cyclePosition = timeSinceChange % totalCycleTime;
    
    // Phase offset for different intersections (to avoid all red at same time)
    const phaseOffset = (index * 5000) % totalCycleTime; // 5 second offset per intersection
    const adjustedCyclePosition = (cyclePosition + phaseOffset) % totalCycleTime;
    
    // Determine state based on cycle position
    if (adjustedCyclePosition < light.greenTime) {
      // Green phase
      newState = 'green';
      // North-South is green first half of cycle, East-West second half
      newCurrentDirection = adjustedCyclePosition < (light.greenTime / 2) ? 'north-south' : 'east-west';
    } else if (adjustedCyclePosition < light.greenTime + light.yellowTime) {
      // Yellow phase
      newState = 'yellow';
      // Keep same direction as was green
    } else {
      // Red phase - brief all-red for safety
      newState = 'red';
    }
    
    // Update state change time only when state actually changes
    if (newState !== light.state) {
      newLastStateChange = currentTime;
    }
    
    return {
      ...light,
      state: newState,
      lastStateChange: newLastStateChange,
      currentDirection: newCurrentDirection,
      cyclePosition: adjustedCyclePosition,
      phaseOffset: phaseOffset
    };
  });
};

// Simple A* pathfinding for road network
export const findPath = (fromIntersectionId, toIntersectionId, roads, intersections) => {
  if (fromIntersectionId === toIntersectionId) {
    return [fromIntersectionId];
  }
  
  // Build adjacency list
  const graph = {};
  intersections.forEach(intersection => {
    graph[intersection.id] = [];
  });
  
  roads.forEach(road => {
    graph[road.from].push({ id: road.to, distance: road.distance });
    graph[road.to].push({ id: road.from, distance: road.distance });
  });
  
  // Simple Dijkstra implementation
  const distances = {};
  const previous = {};
  const unvisited = new Set();
  
  intersections.forEach(intersection => {
    distances[intersection.id] = intersection.id === fromIntersectionId ? 0 : Infinity;
    previous[intersection.id] = null;
    unvisited.add(intersection.id);
  });
  
  while (unvisited.size > 0) {
    // Find unvisited node with minimum distance
    let currentNode = null;
    let minDistance = Infinity;
    
    for (let nodeId of unvisited) {
      if (distances[nodeId] < minDistance) {
        minDistance = distances[nodeId];
        currentNode = nodeId;
      }
    }
    
    if (currentNode === null || currentNode === toIntersectionId) {
      break;
    }
    
    unvisited.delete(currentNode);
    
    // Update distances to neighbors
    if (graph[currentNode]) {
      graph[currentNode].forEach(neighbor => {
        if (unvisited.has(neighbor.id)) {
          const altDistance = distances[currentNode] + neighbor.distance;
          if (altDistance < distances[neighbor.id]) {
            distances[neighbor.id] = altDistance;
            previous[neighbor.id] = currentNode;
          }
        }
      });
    }
  }
  
  // Reconstruct path
  const path = [];
  let currentNode = toIntersectionId;
  
  while (currentNode !== null) {
    path.unshift(currentNode);
    currentNode = previous[currentNode];
  }
  
  return path.length > 1 ? path : null;
};

// Get random intersection for spawning
export const getRandomIntersection = (intersections) => {
  const randomIndex = Math.floor(Math.random() * intersections.length);
  return intersections[randomIndex];
};

// Calculate route duration based on distance and traffic
export const calculateRouteDuration = (path, roads, intersections, trafficLights) => {
  if (!path || path.length < 2) return 5000; // 5 seconds minimum
  
  let totalDistance = 0;
  let totalTime = 0;
  
  for (let i = 0; i < path.length - 1; i++) {
    const fromId = path[i];
    const toId = path[i + 1];
    
    // Find road between these intersections
    const road = roads.find(r => 
      (r.from === fromId && r.to === toId) || 
      (r.from === toId && r.to === fromId)
    );
    
    if (road) {
      totalDistance += road.distance;
      // Calculate time based on speed limit (convert km/h to pixels/ms)
      const speedInPixelsPerMs = (road.speedLimit * 1000) / (3600 * 1000); // very rough conversion
      totalTime += road.distance / speedInPixelsPerMs;
      
      // Add traffic light delay
      const intersection = intersections.find(int => int.id === toId);
      if (intersection && intersection.hasTrafficLight) {
        totalTime += 2000 + Math.random() * 3000; // 2-5 seconds delay
      }
    }
  }
  
  return Math.max(totalTime, 10000); // Minimum 10 seconds
};

// Get waypoints for movement along a path
export const getRouteWaypoints = (path, intersections) => {
  if (!path || path.length === 0) return [];
  
  return path.map(intersectionId => {
    const intersection = intersections.find(int => int.id === intersectionId);
    return intersection ? { x: intersection.x, y: intersection.y } : null;
  }).filter(waypoint => waypoint !== null);
};

// Check if user should stop at traffic light
export const shouldStopAtTrafficLight = (userPosition, trafficLights, userDirection, threshold = 50) => {
  for (let light of trafficLights) {
    const distance = calculateDistance(userPosition.x, userPosition.y, light.x, light.y);
    if (distance <= threshold) {
      // Determine if user is affected by this traffic light based on direction
      const dx = userPosition.vx || 0;
      const dy = userPosition.vy || 0;
      
      // If user is moving horizontally (east-west)
      const isMovingHorizontal = Math.abs(dx) > Math.abs(dy);
      // If user is moving vertically (north-south)  
      const isMovingVertical = Math.abs(dy) > Math.abs(dx);
      
      let shouldStop = false;
      
      if (light.state === 'red') {
        // Always stop on red
        shouldStop = true;
      } else if (light.state === 'yellow') {
        // Stop on yellow if close enough
        shouldStop = distance <= threshold * 0.7;
      } else if (light.state === 'green') {
        // Check if current direction has green light
        if (light.currentDirection === 'north-south' && isMovingHorizontal) {
          shouldStop = true; // East-West traffic should stop
        } else if (light.currentDirection === 'east-west' && isMovingVertical) {
          shouldStop = true; // North-South traffic should stop
        }
      }
      
      if (shouldStop) {
        return light;
      }
    }
  }
  return null;
};
