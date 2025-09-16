// Handle canvas click to add users or select nodes
import useGlobalState from "@/hooks/use-global-state";
import { useCallback } from "react";

export function useMouseUpHandler() {
  const {
    isDraggingNode,
    draggedNode,
    isDraggingUser,
    draggedUser,
    setIsPanning,
    setIsDraggingNode,
    setIsDraggingUser,
    setDraggedNode,
    setDraggedUser,
    setIsDragging,
  } = useGlobalState();

  const handleMouseUp = useCallback(async () => {
    // Handle API call for edge node position update
    if (
      isDraggingNode &&
      draggedNode &&
      draggedNode.node &&
      draggedNode.type === "edge"
    ) {
      try {
        const payload = {
          node_id: draggedNode.node.id,
          coverage: draggedNode.node.coverage || 300.0,
          location: {
            x: Math.round(draggedNode.node.x),
            y: Math.round(draggedNode.node.y),
          },
        };
        // Only make API call if NEXT_PUBLIC_API_URL is available
        if (process.env.NEXT_PUBLIC_API_URL) {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/update_edge_node`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(payload),
            }
          );

          if (!response.ok) {
            console.error(
              "Failed to update edge node position:",
              response.statusText
            );
          }
        }
      } catch (error) {
        console.error("Error updating edge node position:", error);
      }
    }

    // Handle API call for central node position update
    if (
      isDraggingNode &&
      draggedNode &&
      draggedNode.node &&
      draggedNode.type === "central"
    ) {
      try {
        const payload = {
          location: {
            x: Math.round(draggedNode.node.x),
            y: Math.round(draggedNode.node.y),
          },
          coverage: draggedNode.node.coverage || 0,
        };
        if (process.env.NEXT_PUBLIC_API_URL) {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/update_central_node`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            }
          );
          if (!response.ok) {
            console.error(
              "Failed to update central node position:",
              response.statusText
            );
          }
        }
      } catch (error) {
        console.error("Error updating central node position:", error);
      }
    }

    // Handle API call for user position update
    if (isDraggingUser && draggedUser) {
      try {
        const payload = {
          user_id: draggedUser.id,
          location: {
            x: draggedUser.x,
            y: draggedUser.y,
          },
        };
        // Only make API call if NEXT_PUBLIC_API_URL is available
        if (process.env.NEXT_PUBLIC_API_URL) {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/update_user_node`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(payload),
            }
          );

          if (!response.ok) {
            console.error(
              "Failed to update user position:",
              response.statusText
            );
          }
        }
      } catch (error) {
        console.error("Error updating user position:", error);
      }
    }

    setIsPanning(false);
    setIsDraggingNode(false);
    setIsDraggingUser(false);
    setDraggedNode(null);
    setDraggedUser(null);
    setTimeout(() => setIsDragging(false), 100);
  }, [
    isDraggingNode,
    draggedNode,
    isDraggingUser,
    draggedUser,
    setIsPanning,
    setIsDraggingNode,
    setIsDraggingUser,
    setDraggedNode,
    setDraggedUser,
    setIsDragging,
  ]);

  return handleMouseUp;
}
