export const drawRoadNetwork = (ctx, roadNetwork, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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

    // Make roads thicker so they are visible without heavy zoom
    const roadWidth = road.type === 'major' ? 18 / zoomLevel : 10 / zoomLevel;
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
    if (road.direction === 'bidirectional' && zoomLevel > 0.6) {
      // Center line (dashed yellow)
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 1.5 / zoomLevel;
      ctx.setLineDash([10 / zoomLevel, 10 / zoomLevel]);

      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();

      ctx.setLineDash([]); // Reset line dash

      // Lane edges (solid white)
      if (road.type === 'major' && zoomLevel > 0.9) {
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 1.2 / zoomLevel;

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
    // Increase intersection size to match thicker roads
    const intersectionSize = intersection.type === 'major' ? 26 / zoomLevel : 16 / zoomLevel;
    ctx.fillStyle = '#4A5568'; // Slightly lighter than road
    ctx.fillRect(
      intersection.x - intersectionSize / 2,
      intersection.y - intersectionSize / 2,
      intersectionSize,
      intersectionSize
    );

    // Draw crosswalk stripes for major intersections
    if (intersection.type === 'major' && zoomLevel > 1) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.2 / zoomLevel;

      // Horizontal crosswalk
      for (let i = -2; i <= 2; i++) {
        const y = intersection.y + i * 2 / zoomLevel;
        ctx.beginPath();
        ctx.moveTo(intersection.x - intersectionSize / 2, y);
        ctx.lineTo(intersection.x + intersectionSize / 2, y);
        ctx.stroke();
      }

      // Vertical crosswalk  
      for (let i = -2; i <= 2; i++) {
        const x = intersection.x + i * 2 / zoomLevel;
        ctx.beginPath();
        ctx.moveTo(x, intersection.y - intersectionSize / 2);
        ctx.lineTo(x, intersection.y + intersectionSize / 2);
        ctx.stroke();
      }
    }

    // Remove intersection name labels for a cleaner map
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
      light.x - poleWidth / 2,
      light.y - poleHeight,
      poleWidth,
      poleHeight * 1.5
    );

    // Draw traffic light box
    const boxWidth = lightSize * 1.4;
    const boxHeight = lightSize * 2.8;
    ctx.fillStyle = '#1A202C';
    ctx.fillRect(
      light.x - boxWidth / 2,
      light.y - poleHeight - boxHeight / 2,
      boxWidth,
      boxHeight
    );

    // Draw individual lights (red, yellow, green from top to bottom)
    const lightPositions = [
      { y: light.y - poleHeight - boxHeight / 2 + boxHeight / 6, color: '#DC2626', active: light.state === 'red' },     // Red
      { y: light.y - poleHeight - boxHeight / 2 + boxHeight / 2, color: '#D97706', active: light.state === 'yellow' },  // Yellow  
      { y: light.y - poleHeight - boxHeight / 2 + boxHeight * 5 / 6, color: '#059669', active: light.state === 'green' }   // Green
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
        light.y + poleHeight / 2 + fontSize
      );

      // Show which direction is green when zoomed in more
      if (zoomLevel > 2 && light.state === 'green') {
        ctx.fillStyle = '#059669';
        ctx.font = `${fontSize * 0.8}px sans-serif`;
        ctx.fillText(
          directionText,
          light.x,
          light.y + poleHeight / 2 + fontSize * 2
        );
      }
    }
  });
  ctx.restore();
};
