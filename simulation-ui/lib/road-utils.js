import { useEffect } from "react";

export const calculateDistance = (x1, y1, x2, y2) => {
  const dx = x2 - x1;
  const dy = y2 - y1;
  return Math.sqrt(dx * dx + dy * dy);
};

// Road Network Functions
export const createPredefinedRoads = () => {
  const canvasWidth = window.innerWidth;
  const canvasHeight = window.innerHeight;
  
  const predefinedRoads = [
    // Horizontal roads
    {
      id: "road-1",
      startX: 100,
      startY: 200,
      endX: canvasWidth - 100,
      endY: 200,
      width: 40,
      color: "#6B7280",
      type: "highway",
      direction: "bidirectional"
    },
    {
      id: "road-2", 
      startX: 150,
      startY: 400,
      endX: canvasWidth - 150,
      endY: 400,
      width: 30,
      color: "#9CA3AF",
      type: "main",
      direction: "bidirectional"
    },
    {
      id: "road-3",
      startX: 100,
      startY: 600,
      endX: canvasWidth - 200,
      endY: 600,
      width: 25,
      color: "#D1D5DB",
      type: "local",
      direction: "bidirectional"
    },
    // Vertical roads
    {
      id: "road-4",
      startX: 300,
      startY: 100,
      endX: 300,
      endY: canvasHeight - 100,
      width: 35,
      color: "#6B7280",
      type: "highway",
      direction: "bidirectional"
    },
    {
      id: "road-5",
      startX: 600,
      startY: 150,
      endX: 600,
      endY: canvasHeight - 150,
      width: 30,
      color: "#9CA3AF",
      type: "main",
      direction: "bidirectional"
    },
    {
      id: "road-6",
      startX: 900,
      startY: 100,
      endX: 900,
      endY: canvasHeight - 200,
      width: 25,
      color: "#D1D5DB",
      type: "local",
      direction: "bidirectional"
    }
  ];
  
  return predefinedRoads;
};

// Get nearest point on a road to given coordinates
export const getNearestPointOnRoad = (x, y, road) => {
  const dx = road.endX - road.startX;
  const dy = road.endY - road.startY;
  const length = Math.sqrt(dx * dx + dy * dy);
  
  if (length === 0) return { x: road.startX, y: road.startY, t: 0 };
  
  const t = Math.max(0, Math.min(1, ((x - road.startX) * dx + (y - road.startY) * dy) / (length * length)));
  
  return {
    x: road.startX + t * dx,
    y: road.startY + t * dy,
    t: t
  };
};

// Find nearest road to given coordinates
export const findNearestRoad = (x, y, roads) => {
  let nearestRoad = null;
  let minDistance = Infinity;
  let nearestPoint = null;
  
  roads.forEach(road => {
    const point = getNearestPointOnRoad(x, y, road);
    const distance = calculateDistance(x, y, point.x, point.y);
    
    if (distance < minDistance) {
      minDistance = distance;
      nearestRoad = road;
      nearestPoint = point;
    }
  });
  
  return { road: nearestRoad, point: nearestPoint, distance: minDistance };
};

// Move user along road
export const moveUserAlongRoad = (user, road, userSpeed) => {
  const dx = road.endX - road.startX;
  const dy = road.endY - road.startY;
  const length = Math.sqrt(dx * dx + dy * dy);
  
  if (length === 0) return { x: user.x, y: user.y };
  
  // Normalize direction
  const unitX = dx / length;
  const unitY = dy / length;
  
  // Move along road direction
  const speed = userSpeed[0];
  let newX = user.x + unitX * speed * (user.roadDirection || 1);
  let newY = user.y + unitY * speed * (user.roadDirection || 1);
  
  // Check bounds and reverse direction if needed
  const newPoint = getNearestPointOnRoad(newX, newY, road);
  if (newPoint.t <= 0 || newPoint.t >= 1) {
    // Reverse direction
    const newDirection = -(user.roadDirection || 1);
    newX = user.x + unitX * speed * newDirection;
    newY = user.y + unitY * speed * newDirection;
    return { 
      x: newX, 
      y: newY, 
      roadDirection: newDirection,
      constrainedToRoad: true 
    };
  }
  
  return { 
    x: newX, 
    y: newY, 
    roadDirection: user.roadDirection || 1,
    constrainedToRoad: true 
  };
};

export const useRoadInitialization = (setRoads) => {
  // Initialize roads on component mount
  useEffect(() => {
    const roads = createPredefinedRoads();
    setRoads(roads);
  }, [setRoads]);
};
