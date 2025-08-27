import { useCallback } from "react";
import { calculateDistance } from "./helper";
import useSimulationStore from "@/hooks/use-simulation-store";

// Event Handlers
export const useEventHandlers = (state, actions) => {
  const {
    users,
    selectedCentral,
    roadMode,
    roads,
  } = state;

  const {
    isDraggingUser,
    setIsDraggingUser,
    isDraggingNode,
    setIsDraggingNode,
    isDragging,
    setIsDragging,
    panOffset,
    setPanOffset,
    isPanning,
    setIsPanning,
    canvasRef,
    editMode,
    zoomLevel,
    setZoomLevel,
    userSpeed,
    userSize,
    dragOffset,
    setDragOffset,
    draggedNode,
    setDraggedNode,
    draggedUser,
    setDraggedUser,
    lastPanPoint,
    setLastPanPoint,
    edgeNodes,
    setEdgeNodes,
    centralNodes,
    setCentralNodes,
    selectedUser,
    setSelectedUser,
    selectedEdge,
    setSelectedEdge
  } = useSimulationStore();

  const {
    setSelectedCentral,
    setUsers,
  } = actions;

  // Handle canvas click to add users or select nodes
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

  // Handle mouse down for dragging
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
    ]
  );

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

  // Zoom functions
  const zoomIn = useCallback(
    () => setZoomLevel((prev) => Math.min(prev * 1.2, 5)),
    [setZoomLevel]
  );
  const zoomOut = useCallback(
    () => setZoomLevel((prev) => Math.max(prev / 1.2, 0.2)),
    [setZoomLevel]
  );
  const resetZoom = useCallback(() => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  }, [setZoomLevel, setPanOffset]);

  const handleWheel = useCallback(
    (event) => {
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
    },
    [canvasRef, zoomLevel, panOffset, setZoomLevel, setPanOffset]
  );

  const updateEdgeCoverage = useCallback(
    async (nodeId, newCoverage) => {
      try {
        const edgeNode = edgeNodes.find((node) => node.id === nodeId);
        if (!edgeNode) {
          console.error("Edge node not found:", nodeId);
          return;
        }

        const payload = {
          node_id: nodeId,
          coverage: parseFloat(newCoverage),
          location: {
            x: Math.round(edgeNode.x),
            y: Math.round(edgeNode.y),
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
              "Failed to update edge node coverage:",
              response.statusText
            );
            const errorText = await response.text();
            console.error("Error response:", errorText);
          }
        }
      } catch (error) {
        console.error("Error updating edge node coverage:", error);
      }
    },
    [edgeNodes]
  );

  const getCursorStyle = useCallback(() => {
    if (isPanning) return "grabbing";
    if (isDraggingNode || isDraggingUser) return "grabbing";
    if (editMode === "drag") return "grab";
    if (editMode !== "none") return "move";
    return "crosshair";
  }, [isPanning, isDraggingNode, isDraggingUser, editMode]);

  return {
    handleCanvasClick,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleWheel,
    zoomIn,
    zoomOut,
    resetZoom,
    getCursorStyle,
    updateEdgeCoverage,
  };
};
