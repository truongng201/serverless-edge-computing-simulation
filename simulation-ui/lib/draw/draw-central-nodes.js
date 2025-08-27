export const drawCentralNodes = (ctx, centralNodes, selectedCentral, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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