import { React, useEffect } from "react";
import useGlobalState from "@/hooks/use-global-state";
import { getCursorStyle, useWheelHandler } from "@/lib/event-management";

// SimulationCanvas: Handles the canvas drawing and interaction
export default function SimulationCanvas({
  handleCanvasClick,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
}) {
  const { canvasRef } = useGlobalState();
  const handleWheel = useWheelHandler();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Attach non-passive listener
    canvas.addEventListener("wheel", handleWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", handleWheel);
  }, [canvasRef, handleWheel]);

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
