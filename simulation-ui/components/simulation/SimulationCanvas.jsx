import { React, useEffect } from "react";
import useGlobalState from "@/hooks/use-global-state";
import {
  getCursorStyle,
  useWheelHandler,
  useCanvasClickHandler,
  useMouseDownHandler,
  useMouseMoveHandler,
  useMouseUpHandler,
} from "@/lib/event-management";

// SimulationCanvas: Handles the canvas drawing and interaction
export default function SimulationCanvas() {
  const { canvasRef, setCanvasRef } = useGlobalState();
  const handleWheel = useWheelHandler();
  const handleCanvasClick = useCanvasClickHandler();
  const handleMouseDown = useMouseDownHandler();
  const handleMouseMove = useMouseMoveHandler();
  const handleMouseUp = useMouseUpHandler();

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
