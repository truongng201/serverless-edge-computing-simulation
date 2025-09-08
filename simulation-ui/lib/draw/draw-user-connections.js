export const drawUserConnections = (ctx, users, centralNodes, edgeNodes, zoomLevel) => {
  users.forEach((user) => {
    // Only draw for active users with an assignment
    if (!user || user.shouldDespawn) return;
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
