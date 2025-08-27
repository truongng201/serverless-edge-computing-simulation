"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { MapPin, Settings } from "lucide-react";
import ControlPanel from "@/components/simulation/ControlPanel";
import MetricsPanel from "@/components/simulation/MetricsPanel";
import SimulationCanvas from "@/components/simulation/SimulationCanvas";
import EditModeDescription from "@/components/simulation/EditModeDescription";
import ControlPanelContent from "@/components/simulation/ControlPanelContent";
import MetricsPanelContent from "@/components/simulation/MetricsPanelContent";

// Import custom hooks and utilities
import { useEventHandlers } from "@/lib/event-handlers";
import useGlobalState from "@/hooks/use-global-state";
import {
  useSimulationLogic,
  getEditModeDescription,
} from "@/lib/simulation-logic";
import { useCanvasDrawing } from "@/lib/canvas-drawing";
import {
  runPlacementAlgorithm,
  runAssignmentAlgorithm,
  runGAPAssignment,
} from "@/lib/user-management";
import * as NodeManagement from "@/lib/node-management";
import * as UserManagement from "@/lib/user-management";

export default function Component() {
  // Get all state from the custom hook
  const {
    leftPanelOpen,
    setLeftPanelOpen,
    rightPanelOpen,
    setRightPanelOpen,
    edgeNodes,
    setEdgeNodes,
    edgeCoverage,
    placementAlgorithm,
    assignmentAlgorithm,
    centralCoverage,
    centralNodes,
    setCentralNodes,
    setSelectedUser,
    selectedUser,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
    users,
    setUsers,
    simulationData,
  } = useGlobalState();

  // Get event handlers
  const eventHandlers = useEventHandlers();

  // Get simulation logic
  const { simulationStep } = useSimulationLogic();

  // Get canvas drawing
  const { draw } = useCanvasDrawing();

  // Create action objects for easier prop passing
  const nodeActions = {
    addEdgeNode: () =>
      NodeManagement.addEdgeNode(edgeNodes, edgeCoverage, setEdgeNodes),
    removeEdgeNode: () => NodeManagement.removeEdgeNode(),
    addCentralNode: () =>
      NodeManagement.addCentralNode(
        centralNodes,
        centralCoverage,
        setCentralNodes
      ),
    removeCentralNode: () =>
      NodeManagement.removeCentralNode(
        centralNodes,
        selectedCentral,
        setCentralNodes,
        setSelectedCentral
      ),
    deleteSelectedNode: () =>
      NodeManagement.deleteSelectedNode(
        selectedEdge,
        selectedCentral,
        setEdgeNodes,
        setCentralNodes,
        setSelectedEdge,
        setSelectedCentral
      ),
    clearAllUsers: async () =>
      await NodeManagement.clearAllUsers(setUsers, setSelectedUser),
    resetSimulation: () => {
      NodeManagement.resetSimulation(() => nodeActions.clearEverything());
      // Also reset the simulation data if available
      if (simulationData?.resetSimulation) {
        simulationData.resetSimulation();
      }
    },
  };

  const userActions = {
    deleteSelectedUser: async () =>
      await UserManagement.deleteSelectedUser(
        selectedUser,
        setUsers,
        setSelectedUser
      ),
    runPlacementAlgorithm: () =>
      runPlacementAlgorithm(
        users,
        edgeNodes,
        placementAlgorithm,
        setEdgeNodes,
        setUsers
      ),
    runAssignmentAlgorithm: () =>
      runAssignmentAlgorithm(
        users,
        edgeNodes,
        centralNodes,
        assignmentAlgorithm,
        setEdgeNodes,
        setUsers
      ),
    runGAPAssignment: runGAPAssignment,
  };

  // Animation loop
  useEffect(() => {
    const interval = setInterval(() => {
      simulationStep();
      draw();
    }, 100);

    return () => clearInterval(interval);
  }, [simulationStep, draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-gray-50">
      {/* Full Screen Canvas */}
      <SimulationCanvas
        handleCanvasClick={eventHandlers.handleCanvasClick}
        handleMouseDown={eventHandlers.handleMouseDown}
        handleMouseMove={eventHandlers.handleMouseMove}
        handleMouseUp={eventHandlers.handleMouseUp}
        handleWheel={eventHandlers.handleWheel}
        getCursorStyle={eventHandlers.getCursorStyle}
      />

      {/* Left Control Panel */}
      <ControlPanel>
        <ControlPanelContent
          zoomIn={eventHandlers.zoomIn}
          zoomOut={eventHandlers.zoomOut}
          resetZoom={eventHandlers.resetZoom}
          deleteSelectedUser={userActions.deleteSelectedUser}
          simulationStep={simulationStep}
          handleCanvasClick={eventHandlers.handleCanvasClick}
          handleMouseDown={eventHandlers.handleMouseDown}
          handleMouseMove={eventHandlers.handleMouseMove}
          handleMouseUp={eventHandlers.handleMouseUp}
          handleWheel={eventHandlers.handleWheel}
          draw={draw}
          resetSimulation={nodeActions.resetSimulation}
          addEdgeNode={nodeActions.addEdgeNode}
          removeEdgeNode={nodeActions.removeEdgeNode}
          addCentralNode={nodeActions.addCentralNode}
          removeCentralNode={nodeActions.removeCentralNode}
          deleteSelectedNode={nodeActions.deleteSelectedNode}
          clearAllUsers={nodeActions.clearAllUsers}
          clearAllEdgeNodes={nodeActions.clearAllEdgeNodes}
          clearAllCentralNodes={nodeActions.clearAllCentralNodes}
          clearEverything={nodeActions.clearEverything}
          getCursorStyle={eventHandlers.getCursorStyle}
          updateEdgeCoverage={eventHandlers.updateEdgeCoverage}
          runPlacementAlgorithm={userActions.runPlacementAlgorithm}
          runAssignmentAlgorithm={userActions.runAssignmentAlgorithm}
          runGAPAssignment={userActions.runGAPAssignment}
        />
      </ControlPanel>

      {/* Right Metrics Panel */}
      <MetricsPanel>
        <MetricsPanelContent />
      </MetricsPanel>

      {/* Toggle Buttons for Panels */}
      {!leftPanelOpen && (
        <Button
          className="absolute left-4 top-4 z-20"
          size="sm"
          onClick={() => setLeftPanelOpen(true)}
        >
          <Settings className="w-4 h-4" />
        </Button>
      )}
      {!rightPanelOpen && (
        <Button
          className="absolute right-4 top-4 z-20"
          size="sm"
          onClick={() => setRightPanelOpen(true)}
        >
          <MapPin className="w-4 h-4" />
        </Button>
      )}

      {/* Instructions */}
      <EditModeDescription description={getEditModeDescription()} />
    </div>
  );
}
