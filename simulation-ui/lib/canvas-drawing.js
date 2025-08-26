import { useCallback } from "react";

export const useCanvasDrawing = (state) => {
  const {
    canvasRef,
    panOffset,
    zoomLevel,
    roads,
    showRoads,
    centralNodes,
    edgeNodes,
    users,
    selectedCentral,
    selectedEdge,
    selectedUser,
    editMode,
    roadNetwork
  } = state;

  // Drawing function with zoom and pan support
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(panOffset.x, panOffset.y);
    ctx.scale(zoomLevel, zoomLevel);

    const visibleLeft = -panOffset.x / zoomLevel;
    const visibleTop = -panOffset.y / zoomLevel;
    const visibleRight = (canvas.width - panOffset.x) / zoomLevel;
    const visibleBottom = (canvas.height - panOffset.y) / zoomLevel;

    // Draw grid
    drawGrid(ctx, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);

    // Draw roads
    if (showRoads && roads.length > 0) {
      drawRoads(ctx, roads, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);
    }

    // Draw road network (for street map scenario)
    if (roadNetwork) {
      drawRoadNetwork(ctx, roadNetwork, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);
    }

    // Draw connections
    drawConnections(ctx, centralNodes, edgeNodes, zoomLevel);

    // Draw user connections
    drawUserConnections(ctx, users, centralNodes, edgeNodes, zoomLevel);

    // Draw central nodes
    drawCentralNodes(ctx, centralNodes, selectedCentral, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);

    // Draw edge nodes
    drawEdgeNodes(ctx, edgeNodes, selectedEdge, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);

    // Draw users
    drawUsers(ctx, users, selectedUser, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel);

    ctx.restore();
  }, [
    canvasRef,
    panOffset,
    zoomLevel,
    roads,
    showRoads,
    centralNodes,
    edgeNodes,
    users,
    selectedCentral,
    selectedEdge,
    selectedUser,
    editMode,
    roadNetwork
  ]);

  return { draw };
};

const drawGrid = (ctx, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  ctx.strokeStyle = "#f0f0f0";
  ctx.lineWidth = 1 / zoomLevel;
  const gridSize = 50;
  const startX = Math.floor(visibleLeft / gridSize) * gridSize;
  const startY = Math.floor(visibleTop / gridSize) * gridSize;

  for (let i = startX; i <= visibleRight + gridSize; i += gridSize) {
    ctx.beginPath();
    ctx.moveTo(i, visibleTop);
    ctx.lineTo(i, visibleBottom);
    ctx.stroke();
  }
  for (let i = startY; i <= visibleBottom + gridSize; i += gridSize) {
    ctx.beginPath();
    ctx.moveTo(visibleLeft, i);
    ctx.lineTo(visibleRight, i);
    ctx.stroke();
  }
};

const drawRoads = (ctx, roads, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  roads.forEach((road) => {
    // Check if road is visible
    const roadLeft = Math.min(road.startX, road.endX) - road.width;
    const roadRight = Math.max(road.startX, road.endX) + road.width;
    const roadTop = Math.min(road.startY, road.endY) - road.width;
    const roadBottom = Math.max(road.startY, road.endY) + road.width;
    
    if (roadRight < visibleLeft || roadLeft > visibleRight || 
        roadBottom < visibleTop || roadTop > visibleBottom) {
      return;
    }

    // Draw road background (wider)
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = (road.width + 4) / zoomLevel;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(road.startX, road.startY);
    ctx.lineTo(road.endX, road.endY);
    ctx.stroke();

    // Draw road surface
    ctx.strokeStyle = road.color;
    ctx.lineWidth = road.width / zoomLevel;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(road.startX, road.startY);
    ctx.lineTo(road.endX, road.endY);
    ctx.stroke();

    // Draw center line for highways and main roads
    if (road.type === "highway" || road.type === "main") {
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.setLineDash([20 / zoomLevel, 10 / zoomLevel]);
      ctx.beginPath();
      ctx.moveTo(road.startX, road.startY);
      ctx.lineTo(road.endX, road.endY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw road labels
    if (zoomLevel > 0.5) {
      const midX = (road.startX + road.endX) / 2;
      const midY = (road.startY + road.endY) / 2;
      const fontSize = Math.max(8, 12 / zoomLevel);
      
      ctx.fillStyle = "#FFFFFF";
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 3 / zoomLevel;
      ctx.strokeText(road.id, midX, midY);
      ctx.fillText(road.id, midX, midY);
    }
  });
};

const drawConnections = (ctx, centralNodes, edgeNodes, zoomLevel) => {
  // Draw connections between central and edge nodes
  centralNodes.forEach((central) => {
    edgeNodes.forEach((edge) => {
      ctx.strokeStyle = "rgba(99, 101, 241, 0.63)";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.setLineDash([10 / zoomLevel, 5 / zoomLevel]);
      ctx.beginPath();
      ctx.moveTo(central.x, central.y);
      ctx.lineTo(edge.x, edge.y);
      ctx.stroke();
      ctx.setLineDash([]);
    });
  });

  // Draw connections between edge nodes
  for (let i = 0; i < edgeNodes.length; i++) {
    for (let j = i + 1; j < edgeNodes.length; j++) {
      const edgeA = edgeNodes[i];
      const edgeB = edgeNodes[j];
      ctx.strokeStyle = "rgba(16, 185, 129, 0.6)"; // subtle green
      ctx.lineWidth = 1.5 / zoomLevel;
      ctx.setLineDash([6 / zoomLevel, 4 / zoomLevel]);
      ctx.beginPath();
      ctx.moveTo(edgeA.x, edgeA.y);
      ctx.lineTo(edgeB.x, edgeB.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
};

const drawUserConnections = (ctx, users, centralNodes, edgeNodes, zoomLevel) => {
  users.forEach((user, index) => {
    let targetNode = null;
    
    // Find the assigned node
    if (user.assignedCentral) {
      targetNode = centralNodes.find(central => central.id === user.assignedCentral);
    } else if (user.assignedEdge) {
      targetNode = edgeNodes.find(edge => edge.id === user.assignedEdge);
    }
    
    // Draw connection line if target node is found
    if (targetNode) {
      
      // Set line style based on connection type
      if (user.assignedCentral) {
        // Connection to central node - blue color
        ctx.strokeStyle = "rgba(99, 102, 241, 1.0)"; // Made more opaque
        ctx.lineWidth = 3 / zoomLevel; // Made thicker
        ctx.setLineDash([10 / zoomLevel, 5 / zoomLevel]);
      } else {
        // Connection to edge node - green color
        ctx.strokeStyle = "rgba(16, 185, 129, 1.0)"; // Made more opaque
        ctx.lineWidth = 3 / zoomLevel; // Made thicker
        ctx.setLineDash([8 / zoomLevel, 4 / zoomLevel]);
      }
      
      // Draw the connection line
      ctx.beginPath();
      ctx.moveTo(user.x, user.y);
      ctx.lineTo(targetNode.x, targetNode.y);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Draw a small indicator at the user end
      ctx.fillStyle = user.assignedCentral ? "rgba(99, 102, 241, 1.0)" : "rgba(16, 185, 129, 1.0)";
      ctx.beginPath();
      ctx.arc(user.x, user.y, 5 / zoomLevel, 0, 2 * Math.PI); // Made bigger
      ctx.fill();
    }
  });
};

const drawCentralNodes = (ctx, centralNodes, selectedCentral, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  centralNodes.forEach((central) => {
    if (
      central.x + central.coverage < visibleLeft ||
      central.x - central.coverage > visibleRight ||
      central.y + central.coverage < visibleTop ||
      central.y - central.coverage > visibleBottom
    ) {
      return;
    }

    // Coverage area
    if (central.coverage > 0) {
      ctx.fillStyle = `rgba(99, 102, 241, ${
        0.15 + central.currentLoad * 0.005
      })`;
      ctx.strokeStyle = `rgba(99, 102, 241, 0.4)`;
      ctx.lineWidth = 2 / zoomLevel;
      ctx.beginPath();
      ctx.arc(central.x, central.y, central.coverage, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }

    // Central node
    const isSelected = selectedCentral && selectedCentral.id === central.id;
    ctx.fillStyle = isSelected
      ? "#8b5cf6"
      : central.currentLoad > 80
      ? "#dc2626"
      : central.currentLoad > 50
      ? "#ea580c"
      : "#6366f1";

    // Draw diamond shape for central nodes
    const size = isSelected ? 25 : 20;
    ctx.beginPath();
    ctx.moveTo(central.x, central.y - size);
    ctx.lineTo(central.x + size, central.y);
    ctx.lineTo(central.x, central.y + size);
    ctx.lineTo(central.x - size, central.y);
    ctx.closePath();
    ctx.fill();

    // Edit mode indicator for nodes
    if ((editMode === "nodes" || editMode === "both") && !isSelected) {
      ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.setLineDash([5 / zoomLevel, 5 / zoomLevel]);
      ctx.beginPath();
      ctx.arc(central.x, central.y, 30, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = "#8b5cf6";
      ctx.lineWidth = 3 / zoomLevel;
      ctx.beginPath();
      ctx.arc(central.x, central.y, 35, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Label
    const fontSize = Math.max(10, 14 / zoomLevel);
    ctx.fillStyle = "#374151";
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(central.id, central.x, central.y - 45);
    ctx.fillText(
      `${Math.round(central.currentLoad)}%`,
      central.x,
      central.y + 55
    );
  });
};

const drawEdgeNodes = (ctx, edgeNodes, selectedEdge, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  edgeNodes.forEach((edge) => {
    if (
      edge.x + edge.coverage < visibleLeft ||
      edge.x - edge.coverage > visibleRight ||
      edge.y + edge.coverage < visibleTop ||
      edge.y - edge.coverage > visibleBottom
    ) {
      return;
    }

    // Coverage area
    if (edge.coverage > 0) {
      ctx.fillStyle = `rgba(16, 185, 129, ${0.12 + edge.currentLoad * 0.004})`;
      ctx.strokeStyle = `rgba(16, 185, 129, 0.5)`;
      ctx.lineWidth = 1.5 / zoomLevel;
      ctx.beginPath();
      ctx.arc(edge.x, edge.y, edge.coverage, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }

    // Edge node
    const isSelected = selectedEdge && selectedEdge.id === edge.id;
    ctx.fillStyle = isSelected
      ? "#8b5cf6"
      : edge.currentLoad > 80
      ? "#ef4444"
      : edge.currentLoad > 50
      ? "#f59e0b"
      : "#10b981";
    ctx.beginPath();
    ctx.arc(edge.x, edge.y, isSelected ? 20 : 15, 0, 2 * Math.PI);
    ctx.fill();

    // Edit mode indicator for nodes
    if ((editMode === "nodes" || editMode === "both") && !isSelected) {
      ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.setLineDash([5 / zoomLevel, 5 / zoomLevel]);
      ctx.beginPath();
      ctx.arc(edge.x, edge.y, 25, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = "#8b5cf6";
      ctx.lineWidth = 3 / zoomLevel;
      ctx.beginPath();
      ctx.arc(edge.x, edge.y, 25, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Label
    const fontSize = Math.max(10, 14 / zoomLevel);
    ctx.fillStyle = "#374151";
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(edge.id, edge.x, edge.y - 35);
    
    // Handle both decimal (0-1) and percentage (0-100) formats
    const displayLoad = edge.currentLoad <= 1 ? edge.currentLoad * 100 : edge.currentLoad;
    ctx.fillText(`${Math.round(displayLoad)}%`, edge.x, edge.y + 45);
  });
};

const drawUsers = (ctx, users, selectedUser, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  // Reduced logging to avoid console spam
  users.forEach((user) => {
    if (
      user.x < visibleLeft - 50 ||
      user.x > visibleRight + 50 ||
      user.y < visibleTop - 50 ||
      user.y > visibleBottom + 50
    ) {
      return;
    }

    const isSelected = selectedUser && selectedUser.id === user.id;

    // Use special drawing for street map users
    if (user.type === 'street_map') {
      drawStreetMapUser(ctx, user, isSelected, editMode, zoomLevel);
      return;
    }

    // Apply transition properties if they exist
    const opacity = user.opacity !== undefined ? user.opacity : 1;
    const scale = user.scale !== undefined ? user.scale : 1;
    
    // Skip drawing if fully transparent
    if (opacity <= 0) return;

    ctx.save();
    
    // Apply opacity
    ctx.globalAlpha = opacity;
    
    // Apply scale transformation
    if (scale !== 1) {
      ctx.translate(user.x, user.y);
      ctx.scale(scale, scale);
      ctx.translate(-user.x, -user.y);
    }

    // User (isSelected already defined above)
    ctx.fillStyle = isSelected
      ? "#8b5cf6"
      : user.manualConnection
      ? "#f59e0b"
      : "#3b82f6";
    ctx.beginPath();
    ctx.arc(
      user.x,
      user.y,
      isSelected ? user.size + 2 : user.size,
      0,
      2 * Math.PI
    );
    ctx.fill();

    // Edit mode indicator for users
    if ((editMode === "users" || editMode === "both") && !isSelected) {
      ctx.strokeStyle = "rgba(139, 92, 246, 0.5)";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.setLineDash([3 / zoomLevel, 3 / zoomLevel]);
      ctx.beginPath();
      ctx.arc(user.x, user.y, user.size + 8, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = "#8b5cf6";
      ctx.lineWidth = 2 / zoomLevel;
      ctx.beginPath();
      ctx.arc(user.x, user.y, user.size + 6, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Latency indicator
    const latencyColor =
      user.latency > 50
        ? "#ef4444"
        : user.latency > 25
        ? "#f59e0b"
        : "#10b981";
    ctx.fillStyle = latencyColor;
    ctx.beginPath();
    ctx.arc(user.x, user.y, 3, 0, 2 * Math.PI);
    ctx.fill();

    // User ID for selected user
    if (isSelected) {
      const fontSize = Math.max(8, 12 / zoomLevel);
      ctx.fillStyle = "#374151";
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(user.id, user.x, user.y - user.size - 10);
    }
    
    ctx.restore();
  });
};

// Draw road network for street map scenario
const drawRoadNetwork = (ctx, roadNetwork, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  const { roads, intersections, trafficLights } = roadNetwork;
  
  // Draw roads with bidirectional lanes
  ctx.save();
  roads.forEach(road => {
    const from = intersections.find(int => int.id === road.from);
    const to = intersections.find(int => int.id === road.to);
    
    if (!from || !to) return;
    
    // Check if road is in visible area
    if (
      Math.max(from.x, to.x) < visibleLeft ||
      Math.min(from.x, to.x) > visibleRight ||
      Math.max(from.y, to.y) < visibleTop ||
      Math.min(from.y, to.y) > visibleBottom
    ) return;
    
    // Calculate road direction and perpendicular offset for lanes
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const unitX = dx / length;
    const unitY = dy / length;
    const perpX = -unitY; // Perpendicular for lane separation
    const perpY = unitX;
    
    const roadWidth = road.type === 'major' ? 8 / zoomLevel : 4 / zoomLevel;
    const laneOffset = roadWidth / 4;
    
    // Draw road background (asphalt)
    ctx.strokeStyle = '#2D3748'; // Dark gray asphalt
    ctx.lineWidth = roadWidth;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
    
    // Draw lane dividers for bidirectional roads
    if (road.direction === 'bidirectional' && zoomLevel > 0.8) {
      // Center line (dashed yellow)
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 1 / zoomLevel;
      ctx.setLineDash([8 / zoomLevel, 8 / zoomLevel]);
      
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
      
      ctx.setLineDash([]); // Reset line dash
      
      // Lane edges (solid white)
      if (road.type === 'major' && zoomLevel > 1.2) {
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 0.8 / zoomLevel;
        
        // Left edge
        ctx.beginPath();
        ctx.moveTo(from.x + perpX * laneOffset * 2, from.y + perpY * laneOffset * 2);
        ctx.lineTo(to.x + perpX * laneOffset * 2, to.y + perpY * laneOffset * 2);
        ctx.stroke();
        
        // Right edge
        ctx.beginPath();
        ctx.moveTo(from.x - perpX * laneOffset * 2, from.y - perpY * laneOffset * 2);
        ctx.lineTo(to.x - perpX * laneOffset * 2, to.y - perpY * laneOffset * 2);
        ctx.stroke();
      }
    }
  });
  ctx.restore();
  
  // Draw intersections
  ctx.save();
  intersections.forEach(intersection => {
    // Check if intersection is in visible area
    if (
      intersection.x < visibleLeft || intersection.x > visibleRight ||
      intersection.y < visibleTop || intersection.y > visibleBottom
    ) return;
    
    // Draw intersection area (lighter asphalt for intersection)
    const intersectionSize = intersection.type === 'major' ? 16 / zoomLevel : 10 / zoomLevel;
    ctx.fillStyle = '#4A5568'; // Slightly lighter than road
    ctx.fillRect(
      intersection.x - intersectionSize/2, 
      intersection.y - intersectionSize/2, 
      intersectionSize, 
      intersectionSize
    );
    
    // Draw crosswalk stripes for major intersections
    if (intersection.type === 'major' && zoomLevel > 1) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1 / zoomLevel;
      
      // Horizontal crosswalk
      for (let i = -2; i <= 2; i++) {
        const y = intersection.y + i * 2 / zoomLevel;
        ctx.beginPath();
        ctx.moveTo(intersection.x - intersectionSize/2, y);
        ctx.lineTo(intersection.x + intersectionSize/2, y);
        ctx.stroke();
      }
      
      // Vertical crosswalk  
      for (let i = -2; i <= 2; i++) {
        const x = intersection.x + i * 2 / zoomLevel;
        ctx.beginPath();
        ctx.moveTo(x, intersection.y - intersectionSize/2);
        ctx.lineTo(x, intersection.y + intersectionSize/2);
        ctx.stroke();
      }
    }
    
    // Draw intersection name for major intersections when zoomed in
    if (intersection.type === 'major' && zoomLevel > 1.8) {
      const fontSize = Math.max(8, 12 / zoomLevel);
      ctx.fillStyle = '#1F2937';
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(intersection.name, intersection.x, intersection.y - intersectionSize/2 - 8);
    }
  });
  ctx.restore();
  
  // Draw traffic lights
  ctx.save();
  trafficLights.forEach(light => {
    // Check if traffic light is in visible area
    if (
      light.x < visibleLeft || light.x > visibleRight ||
      light.y < visibleTop || light.y > visibleBottom
    ) return;
    
    const lightSize = Math.max(4, 10 / zoomLevel);
    const poleHeight = lightSize * 2.5;
    const poleWidth = lightSize * 0.3;
    
    // Draw traffic light pole
    ctx.fillStyle = '#2D3748';
    ctx.fillRect(
      light.x - poleWidth/2, 
      light.y - poleHeight, 
      poleWidth, 
      poleHeight * 1.5
    );
    
    // Draw traffic light box
    const boxWidth = lightSize * 1.4;
    const boxHeight = lightSize * 2.8;
    ctx.fillStyle = '#1A202C';
    ctx.fillRect(
      light.x - boxWidth/2,
      light.y - poleHeight - boxHeight/2,
      boxWidth,
      boxHeight
    );
    
    // Draw individual lights (red, yellow, green from top to bottom)
    const lightPositions = [
      { y: light.y - poleHeight - boxHeight/2 + boxHeight/6, color: '#DC2626', active: light.state === 'red' },     // Red
      { y: light.y - poleHeight - boxHeight/2 + boxHeight/2, color: '#D97706', active: light.state === 'yellow' },  // Yellow  
      { y: light.y - poleHeight - boxHeight/2 + boxHeight*5/6, color: '#059669', active: light.state === 'green' }   // Green
    ];
    
    lightPositions.forEach(lightPos => {
      const radius = lightSize * 0.3;
      
      // Light background (dark when inactive)
      ctx.fillStyle = lightPos.active ? lightPos.color : '#374151';
      ctx.beginPath();
      ctx.arc(light.x, lightPos.y, radius, 0, 2 * Math.PI);
      ctx.fill();
      
      // Light glow effect when active
      if (lightPos.active) {
        ctx.save();
        ctx.shadowColor = lightPos.color;
        ctx.shadowBlur = 8;
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = lightPos.color;
        ctx.beginPath();
        ctx.arc(light.x, lightPos.y, radius * 0.8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.restore();
        
        // Extra bright center
        ctx.fillStyle = '#FFFFFF';
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.arc(light.x, lightPos.y, radius * 0.4, 0, 2 * Math.PI);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      
      // Light rim
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.arc(light.x, lightPos.y, radius, 0, 2 * Math.PI);
      ctx.stroke();
    });
    
    // Draw state indicator text when zoomed in
    if (zoomLevel > 1.5) {
      const fontSize = Math.max(6, 8 / zoomLevel);
      ctx.fillStyle = '#1F2937';
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      
      // Show state and current direction
      const stateText = light.state.toUpperCase();
      const directionText = light.currentDirection === 'north-south' ? 'N-S' : 'E-W';
      
      ctx.fillText(
        `${stateText}`, 
        light.x, 
        light.y + poleHeight/2 + fontSize
      );
      
      // Show which direction is green when zoomed in more
      if (zoomLevel > 2 && light.state === 'green') {
        ctx.fillStyle = '#059669';
        ctx.font = `${fontSize * 0.8}px sans-serif`;
        ctx.fillText(
          directionText, 
          light.x, 
          light.y + poleHeight/2 + fontSize * 2
        );
      }
    }
  });
  ctx.restore();
};

// Enhanced user drawing for street map users
const drawStreetMapUser = (ctx, user, isSelected, editMode, zoomLevel) => {
  if (user.type !== 'street_map') return;
  
  ctx.save();
  
  // Vehicle body (rectangular for cars)
  const width = user.size * 1.5;
  const height = user.size;
  
  ctx.translate(user.x, user.y);
  ctx.rotate(user.direction || 0);
  
  // Vehicle shadow
  ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
  ctx.fillRect(-width/2 + 1, -height/2 + 1, width, height);
  
  // Vehicle body
  ctx.fillStyle = user.color || '#3B82F6';
  ctx.fillRect(-width/2, -height/2, width, height);
  
  // Vehicle outline
  ctx.strokeStyle = '#1F2937';
  ctx.lineWidth = 1 / zoomLevel;
  ctx.strokeRect(-width/2, -height/2, width, height);
  
  // Vehicle details (when zoomed in)
  if (zoomLevel > 1.5) {
    // Windows
    ctx.fillStyle = '#87CEEB';
    ctx.fillRect(-width/2 + 2, -height/2 + 1, width - 4, height/3);
    
    // Headlights
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(width/2 - 1, -height/2 + 1, 1, 2);
    ctx.fillRect(width/2 - 1, height/2 - 3, 1, 2);
  }
  
  ctx.restore();
  
  // Selection ring
  if (isSelected) {
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 2 / zoomLevel;
    ctx.beginPath();
    ctx.arc(user.x, user.y, Math.max(width, height) / 2 + 4, 0, 2 * Math.PI);
    ctx.stroke();
  }
  
  // Status indicator
  if (user.isWaitingAtLight) {
    // Red dot for waiting at traffic light
    ctx.fillStyle = '#EF4444';
    ctx.beginPath();
    ctx.arc(user.x + width/2 + 5, user.y - height/2 - 5, 3, 0, 2 * Math.PI);
    ctx.fill();
  } else if (user.isMoving) {
    // Green dot for moving
    ctx.fillStyle = '#10B981';
    ctx.beginPath();
    ctx.arc(user.x + width/2 + 5, user.y - height/2 - 5, 3, 0, 2 * Math.PI);
    ctx.fill();
  }
};
