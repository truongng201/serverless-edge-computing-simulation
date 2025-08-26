export const drawGrid = (ctx, visibleLeft, visibleTop, visibleRight, visibleBottom, zoomLevel) => {
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
