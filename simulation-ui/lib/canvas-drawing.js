import { useCallback } from "react";
import {
  drawGrid,
  drawUsers,
  drawRoads,
  drawRoadNetwork,
  drawConnections,
  drawUserConnections,
  drawCentralNodes,
  drawEdgeNodes,
} from "./draw";
import useSimulationStore from "@/hooks/use-simulation-store";

export const useCanvasDrawing = (state) => {
  const {
    roads,
    showRoads,
    users,
    selectedCentral,
    selectedEdge,
    selectedUser,
  } = state;
  const {
    panOffset,
    canvasRef,
    editMode,
    zoomLevel,
    roadNetwork,
    edgeNodes,
    centralNodes,
  } = useSimulationStore();

  // Drawing function with zoom and pan support
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(panOffset.x, panOffset.y);
    ctx.scale(zoomLevel, zoomLevel);

    const visibleLeft = -panOffset.x / zoomLevel;
    const visibleTop = -panOffset.y / zoomLevel;
    const visibleRight = (canvas.width - panOffset.x) / zoomLevel;
    const visibleBottom = (canvas.height - panOffset.y) / zoomLevel;

    drawGrid(
      ctx,
      visibleLeft,
      visibleTop,
      visibleRight,
      visibleBottom,
      zoomLevel
    );

    if (showRoads && roads.length > 0) {
      drawRoads(
        ctx,
        roads,
        visibleLeft,
        visibleTop,
        visibleRight,
        visibleBottom,
        zoomLevel
      );
    }

    if (roadNetwork) {
      drawRoadNetwork(
        ctx,
        roadNetwork,
        visibleLeft,
        visibleTop,
        visibleRight,
        visibleBottom,
        zoomLevel
      );
    }

    drawConnections(ctx, centralNodes, edgeNodes, zoomLevel);

    drawUserConnections(ctx, users, centralNodes, edgeNodes, zoomLevel);

    drawCentralNodes(
      ctx,
      centralNodes,
      selectedCentral,
      editMode,
      visibleLeft,
      visibleTop,
      visibleRight,
      visibleBottom,
      zoomLevel
    );

    drawEdgeNodes(
      ctx,
      edgeNodes,
      selectedEdge,
      editMode,
      visibleLeft,
      visibleTop,
      visibleRight,
      visibleBottom,
      zoomLevel
    );

    drawUsers(
      ctx,
      users,
      selectedUser,
      editMode,
      visibleLeft,
      visibleTop,
      visibleRight,
      visibleBottom,
      zoomLevel
    );

    ctx.restore();
  }, [
    canvasRef,
    panOffset,
    zoomLevel,
    roads,
    showRoads,
    centralNodes,
    edgeNodes,
    users,
    selectedCentral,
    selectedEdge,
    selectedUser,
    editMode,
    roadNetwork,
  ]);

  return { draw };
};
