export const drawEdgeNodes = (ctx, edgeNodes, selectedEdge, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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