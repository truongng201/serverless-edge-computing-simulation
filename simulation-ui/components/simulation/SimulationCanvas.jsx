import { React, useEffect } from "react";
import useSimulationStore from "@/hooks/use-simulation-store";

// SimulationCanvas: Handles the canvas drawing and interaction
export default function SimulationCanvas({
  handleCanvasClick,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleWheel,
  getCursorStyle,
}) {
  const { canvasRef, setCanvasRef } = useSimulationStore();
  useEffect(() => {
    const ref = { current: null };
    setCanvasRef(ref);
  }, [setCanvasRef]);
  return (
    <canvas
      ref={(el) => (canvasRef.current = el)}
      className="absolute inset-0 bg-white"
      onClick={handleCanvasClick}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: getCursorStyle() }}
    />
  );
}
