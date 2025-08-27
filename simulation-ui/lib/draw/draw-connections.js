export const drawConnections = (ctx, centralNodes, edgeNodes, zoomLevel) => {
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