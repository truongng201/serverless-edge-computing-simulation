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
    editMode
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

    // Draw connections
    drawConnections(ctx, centralNodes, edgeNodes, zoomLevel);

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
    editMode
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
    ctx.fillText(`${Math.round(edge.currentLoad)}%`, edge.x, edge.y + 45);
  });
};

const drawUsers = (ctx, users, selectedUser, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
  // Reduced logging to avoid console spam
  if (users.length > 0 && Math.random() < 0.1) { // Log only occasionally
    console.log(`Rendering ${users.length} users`);
  }
  users.forEach((user) => {
    if (
      user.x < visibleLeft - 50 ||
      user.x > visibleRight + 50 ||
      user.y < visibleTop - 50 ||
      user.y > visibleBottom + 50
    ) {
      return;
    }

    // User
    const isSelected = selectedUser && selectedUser.id === user.id;
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
  });
};
