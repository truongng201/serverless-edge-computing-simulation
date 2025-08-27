// Handle canvas click to add users or select nodes
import useGlobalState from "@/hooks/use-global-state";
import { useCallback } from "react";
import { calculateDistance } from "../helper";

export function useCanvasClickHandler() {
  const {
    isDragging,
    isPanning,
    isDraggingNode,
    isDraggingUser,
    canvasRef,
    panOffset,
    zoomLevel,
    edgeNodes,
    centralNodes,
    users,
    editMode,
    roadMode,
    roads,
    userSpeed,
    userSize,
    setSelectedEdge,
    setSelectedCentral,
    setSelectedUser,
    setUsers,
  } = useGlobalState();

  const handleCanvasClick = useCallback(
    (event) => {
      if (isDragging || isPanning || isDraggingNode || isDraggingUser) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      const worldX = (screenX - panOffset.x) / zoomLevel;
      const worldY = (screenY - panOffset.y) / zoomLevel;

      // Check for node selection first
      const clickedEdge = edgeNodes.find(
        (edge) => calculateDistance(worldX, worldY, edge.x, edge.y) < 20
      );
      const clickedCentral = centralNodes.find(
        (central) =>
          calculateDistance(worldX, worldY, central.x, central.y) < 25
      );
      const clickedUser = users.find(
        (user) =>
          calculateDistance(worldX, worldY, user.x, user.y) < user.size + 5
      );

      if (clickedEdge) {
        setSelectedEdge(clickedEdge);
        setSelectedCentral(null);
        setSelectedUser(null);
        return;
      }

      if (clickedCentral) {
        setSelectedCentral(clickedCentral);
        setSelectedEdge(null);
        setSelectedUser(null);
        return;
      }

      if (clickedUser) {
        setSelectedUser(clickedUser);
        setSelectedEdge(null);
        setSelectedCentral(null);
        return;
      }

      // Clear selections and add user if not in edit mode or drag mode
      setSelectedUser(null);
      setSelectedEdge(null);
      setSelectedCentral(null);

      if (editMode === "none") {
        let userX = worldX;
        let userY = worldY;
        let assignedRoad = null;
        let roadDirection = Math.random() > 0.5 ? 1 : -1;

        // If road mode is enabled, snap user to nearest road
        if (roadMode && roads.length > 0) {
          const nearest = findNearestRoad(worldX, worldY, roads);
          if (nearest.road && nearest.distance < 50) {
            // Allow placing within 50px of road
            userX = nearest.point.x;
            userY = nearest.point.y;
            assignedRoad = nearest.road.id;
          }
        }

        const newUser = {
          id: `user-${Date.now()}`,
          x: userX,
          y: userY,
          vx: roadMode ? 0 : (Math.random() - 0.5) * userSpeed[0], // No random velocity in road mode
          vy: roadMode ? 0 : (Math.random() - 0.5) * userSpeed[0],
          predictedPath: [],
          assignedEdge: null,
          assignedCentral: null,
          latency: 0,
          size: userSize[0],
          manualConnection: false,
          assignedRoad: assignedRoad,
          roadDirection: roadDirection,
          constrainedToRoad: roadMode && assignedRoad !== null,
        };
        setUsers((prev) => [...prev, newUser]);

        // Call API to create user node
        try {
          const payload = {
            user_id: newUser.id,
            location: {
              x: userX,
              y: userY,
            },
            speed: userSpeed[0],
            size: userSize[0],
          };

          // Only make API call if NEXT_PUBLIC_API_URL is available
          if (process.env.NEXT_PUBLIC_API_URL) {
            fetch(
              `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/create_user_node`,
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
              }
            )
              .then((response) => {
                if (!response.ok) {
                  console.error(
                    "Failed to create user node:",
                    response.statusText
                  );
                }
              })
              .catch((error) => {
                console.error("Error creating user node:", error);
              });
          }
        } catch (error) {
          console.error("Error preparing user node creation:", error);
        }
      }
    },
    [
      isDragging,
      isPanning,
      isDraggingNode,
      isDraggingUser,
      canvasRef,
      panOffset,
      zoomLevel,
      edgeNodes,
      centralNodes,
      users,
      editMode,
      roadMode,
      roads,
      userSpeed,
      userSize,
      setSelectedEdge,
      setSelectedCentral,
      setSelectedUser,
      setUsers,
    ]
  );

  return handleCanvasClick;
}
