export const drawStreetMapUser = (ctx, user, isSelected, editMode, zoomLevel) => {
  if (user.type !== 'street_map') return;

  ctx.save();

  // Vehicle body (rectangular for cars)
  const width = user.size * 1.5;
  const height = user.size;

  ctx.translate(user.x, user.y);
  ctx.rotate(user.direction || 0);

  // Vehicle shadow
  ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
  ctx.fillRect(-width / 2 + 1, -height / 2 + 1, width, height);

  // Vehicle body
  ctx.fillStyle = user.color || '#3B82F6';
  ctx.fillRect(-width / 2, -height / 2, width, height);

  // Vehicle outline
  ctx.strokeStyle = '#1F2937';
  ctx.lineWidth = 1 / zoomLevel;
  ctx.strokeRect(-width / 2, -height / 2, width, height);

  // Vehicle details (when zoomed in)
  if (zoomLevel > 1.5) {
    // Windows
    ctx.fillStyle = '#87CEEB';
    ctx.fillRect(-width / 2 + 2, -height / 2 + 1, width - 4, height / 3);

    // Headlights
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(width / 2 - 1, -height / 2 + 1, 1, 2);
    ctx.fillRect(width / 2 - 1, height / 2 - 3, 1, 2);
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
    ctx.arc(user.x + width / 2 + 5, user.y - height / 2 - 5, 3, 0, 2 * Math.PI);
    ctx.fill();
  } else if (user.isMoving) {
    // Green dot for moving
    ctx.fillStyle = '#10B981';
    ctx.beginPath();
    ctx.arc(user.x + width / 2 + 5, user.y - height / 2 - 5, 3, 0, 2 * Math.PI);
    ctx.fill();
  }
};