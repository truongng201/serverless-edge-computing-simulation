import { drawStreetMapUser } from "./draw-street-map-user";

export const drawUsers = (ctx, users, selectedUser, editMode, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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