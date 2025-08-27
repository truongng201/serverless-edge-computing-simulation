// Handle canvas click to add users or select nodes
import useGlobalState from "@/hooks/use-global-state";
import { useCallback } from "react";

export function useMouseMoveHandler() {
  const {
    isPanning,
    lastPanPoint,
    isDraggingUser,
    draggedUser,
    isDraggingNode,
    draggedNode,
    canvasRef,
    panOffset,
    zoomLevel,
    dragOffset,
    selectedUser,
    selectedEdge,
    selectedCentral,
    setPanOffset,
    setLastPanPoint,
    setUsers,
    setSelectedUser,
    setSelectedEdge,
    setSelectedCentral,
    setEdgeNodes,
    setCentralNodes,
    setIsDragging,
    setDraggedNode,
    setDraggedUser
  } = useGlobalState();

  const handleMouseMove = useCallback(
    (event) => {
      if (isPanning) {
        const deltaX = event.clientX - lastPanPoint.x;
        const deltaY = event.clientY - lastPanPoint.y;
        setPanOffset((prev) => ({
          x: prev.x + deltaX,
          y: prev.y + deltaY,
        }));
        setLastPanPoint({ x: event.clientX, y: event.clientY });
      } else if (isDraggingUser && draggedUser) {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const screenX = event.clientX - rect.left;
        const screenY = event.clientY - rect.top;
        const worldX = (screenX - panOffset.x) / zoomLevel;
        const worldY = (screenY - panOffset.y) / zoomLevel;

        const newX = worldX - dragOffset.x;
        const newY = worldY - dragOffset.y;

        setUsers((prev) =>
          prev.map((user) =>
            user.id === draggedUser.id ? { ...user, x: newX, y: newY } : user
          )
        );

        // Update draggedUser with current position for API call
        setDraggedUser((prev) => ({ ...prev, x: newX, y: newY }));

        // Update selected user if it's the one being dragged
        if (selectedUser && selectedUser.id === draggedUser.id) {
          setSelectedUser((prev) => ({ ...prev, x: newX, y: newY }));
        }
      } else if (isDraggingNode && draggedNode && draggedNode.node) {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const screenX = event.clientX - rect.left;
        const screenY = event.clientY - rect.top;
        const worldX = (screenX - panOffset.x) / zoomLevel;
        const worldY = (screenY - panOffset.y) / zoomLevel;

        const newX = worldX - dragOffset.x;
        const newY = worldY - dragOffset.y;

        if (draggedNode.type === "edge") {
          setEdgeNodes((prev) =>
            prev.map((edge) =>
              edge.id === draggedNode.node.id
                ? { ...edge, x: newX, y: newY }
                : edge
            )
          );
          // Update draggedNode with current position for API call
          setDraggedNode((prev) => ({
            ...prev,
            node: prev.node ? { ...prev?.node, x: newX, y: newY } : null,
          }));

          // Update selected edge if it's the one being dragged
          if (selectedEdge && selectedEdge.id === draggedNode.node.id) {
            setSelectedEdge((prev) => ({ ...prev, x: newX, y: newY }));
          }
        } else if (draggedNode.type === "central") {
          setCentralNodes((prev) =>
            prev.map((central) =>
              central.id === draggedNode.node.id
                ? { ...central, x: newX, y: newY }
                : central
            )
          );
          // Update draggedNode with current position
          setDraggedNode((prev) => ({
            ...prev,
            node: prev.node ? { ...prev.node, x: newX, y: newY } : null,
          }));

          // Update selected central if it's the one being dragged
          if (selectedCentral && selectedCentral.id === draggedNode.node.id) {
            setSelectedCentral((prev) => ({ ...prev, x: newX, y: newY }));
          }
        }
      } else {
        setIsDragging(true);
      }
    },
    [
      isPanning,
      lastPanPoint,
      isDraggingUser,
      draggedUser,
      isDraggingNode,
      draggedNode,
      canvasRef,
      panOffset,
      zoomLevel,
      dragOffset,
      selectedUser,
      selectedEdge,
      selectedCentral,
      setPanOffset,
      setLastPanPoint,
      setUsers,
      setSelectedUser,
      setSelectedEdge,
      setSelectedCentral,
      setEdgeNodes,
      setCentralNodes,
      setIsDragging,
      setDraggedNode,
      setDraggedUser
    ]
  );

  return handleMouseMove;
}
