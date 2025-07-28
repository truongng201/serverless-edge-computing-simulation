import React from "react"

// SimulationCanvas: Handles the canvas drawing and interaction
export default function SimulationCanvas({
  canvasRef,
  handleCanvasClick,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleWheel,
  getCursorStyle,
}) {
  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 bg-white"
      onClick={handleCanvasClick}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: getCursorStyle() }}
    />
  )
}
