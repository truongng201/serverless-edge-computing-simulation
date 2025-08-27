// Handle canvas click to add users or select nodes
import useGlobalState from "@/hooks/use-global-state";
import { useCallback } from "react";
import { calculateDistance } from "../helper";
import { useCanvasClickHandler } from "./handle-canvas-click";

export function useMouseDownHandler() {
  const {
    editMode,
    canvasRef,
    panOffset,
    zoomLevel,
    users,
    edgeNodes,
    centralNodes,
    setIsPanning,
    setLastPanPoint,
    setIsDraggingUser,
    setDraggedUser,
    setDragOffset,
    setIsDraggingNode,
    setDraggedNode,
    setIsDragging,
    setSelectedEdge,
    setSelectedUser,
    setSelectedCentral
  } = useGlobalState();
  const handleCanvasClick = useCanvasClickHandler()
  const handleMouseDown = useCallback(
    (event) => {
      if (
        event.button === 1 ||
        (event.button === 0 && event.ctrlKey && editMode === "none") ||
        (event.button === 0 && editMode === "drag")
      ) {
        setIsPanning(true);
        setLastPanPoint({ x: event.clientX, y: event.clientY });
        event.preventDefault();
        return;
      }

      if (editMode !== "none" && editMode !== "drag") {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const screenX = event.clientX - rect.left;
        const screenY = event.clientY - rect.top;
        const worldX = (screenX - panOffset.x) / zoomLevel;
        const worldY = (screenY - panOffset.y) / zoomLevel;

        // Check for user dragging first (if users edit mode is enabled)
        if (editMode === "users" || editMode === "both") {
          const clickedUser = users.find(
            (user) =>
              calculateDistance(worldX, worldY, user.x, user.y) < user.size + 5
          );
          if (clickedUser) {
            setIsDraggingUser(true);
            setDraggedUser(clickedUser);
            setDragOffset({
              x: worldX - clickedUser.x,
              y: worldY - clickedUser.y,
            });
            event.preventDefault();
            return;
          }
        }

        // Check for node dragging (if nodes edit mode is enabled)
        if (editMode === "nodes" || editMode === "both") {
          const clickedEdge = edgeNodes.find(
            (edge) => calculateDistance(worldX, worldY, edge.x, edge.y) < 20
          );
          const clickedCentral = centralNodes.find(
            (central) =>
              calculateDistance(worldX, worldY, central.x, central.y) < 25
          );

          if (clickedEdge) {
            setIsDraggingNode(true);
            setDraggedNode({ type: "edge", node: clickedEdge });
            setDragOffset({
              x: worldX - clickedEdge.x,
              y: worldY - clickedEdge.y,
            });
            // Set the edge as selected to show the purple circle
            setSelectedEdge(clickedEdge);
            setSelectedCentral(null);
            setSelectedUser(null);
            event.preventDefault();
            return;
          }

          if (clickedCentral) {
            setIsDraggingNode(true);
            setDraggedNode({ type: "central", node: clickedCentral });
            setDragOffset({
              x: worldX - clickedCentral.x,
              y: worldY - clickedCentral.y,
            });
            // Set the central as selected to show the purple circle
            setSelectedCentral(clickedCentral);
            setSelectedEdge(null);
            setSelectedUser(null);
            event.preventDefault();
            return;
          }
        }
      }

      setIsDragging(false);
      handleCanvasClick(event);
    },
    [
      editMode,
      canvasRef,
      panOffset,
      zoomLevel,
      users,
      edgeNodes,
      centralNodes,
      setIsPanning,
      setLastPanPoint,
      setIsDraggingUser,
      setDraggedUser,
      setDragOffset,
      setIsDraggingNode,
      setDraggedNode,
      setIsDragging,
      handleCanvasClick,
    ]
  );

  return handleMouseDown;
}
