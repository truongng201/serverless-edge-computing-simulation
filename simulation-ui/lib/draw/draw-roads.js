export const drawRoads = (
  ctx,
  roads,
  visibleLeft,
  visibleTop,
  visibleRight,
  visibleBottom,
  zoomLevel
) => {
  if (!roads || roads.length === 0) return;

  const lineWidth = Math.max(0.5, 1.0 / (zoomLevel || 1));
  ctx.lineWidth = lineWidth;
  ctx.strokeStyle = "#8ea3b0"; // soft blue-gray
  ctx.globalAlpha = 0.75;

  for (const poly of roads) {
    if (!poly || poly.length < 2) continue;

    // Quick culling: skip if polyline is entirely outside visible box
    let skip = true;
    for (const [x, y] of poly) {
      if (x >= visibleLeft && x <= visibleRight && y >= visibleTop && y <= visibleBottom) {
        skip = false;
        break;
      }
    }
    if (skip) continue;

    ctx.beginPath();
    ctx.moveTo(poly[0][0], poly[0][1]);
    for (let i = 1; i < poly.length; i++) {
      ctx.lineTo(poly[i][0], poly[i][1]);
    }
    ctx.stroke();
  }

  ctx.globalAlpha = 1.0;
};

