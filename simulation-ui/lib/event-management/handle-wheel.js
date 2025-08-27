import useGlobalState from "@/hooks/use-global-state";
import { useCallback } from "react";

/**
 * Hook that sets up a wheel handler for zoom/pan
 * and automatically attaches/removes the listener with { passive: false }.
 */
export function useWheelHandler() {
  const { canvasRef, zoomLevel, panOffset, setZoomLevel, setPanOffset } =
    useGlobalState();

  const handleWheel = useCallback((event) => {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.2, Math.min(5, zoomLevel * zoomFactor));

    const zoomRatio = newZoom / zoomLevel;
    const newPanX = mouseX - (mouseX - panOffset.x) * zoomRatio;
    const newPanY = mouseY - (mouseY - panOffset.y) * zoomRatio;

    setZoomLevel(newZoom);
    setPanOffset({ x: newPanX, y: newPanY });
  }, [canvasRef, zoomLevel, panOffset, setZoomLevel, setPanOffset]);

  return handleWheel;
}
