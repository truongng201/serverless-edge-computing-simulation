export const drawRoads = (ctx, roads, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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