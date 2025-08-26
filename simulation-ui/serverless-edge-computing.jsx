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
import { useSimulationState } from "@/hooks/use-simulation-state";
import { useEventHandlers } from "@/lib/event-handlers";
import useSimulationStore from "@/hooks/use-simulation-store";
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
  const state = useSimulationState();
  const { leftPanelOpen, setLeftPanelOpen, rightPanelOpen, setRightPanelOpen } = useSimulationStore();

  // Get event handlers
  const eventHandlers = useEventHandlers(state, state);

  // Get simulation logic
  const { simulationStep } = useSimulationLogic(state, state);

  // Get canvas drawing
  const { draw } = useCanvasDrawing(state);


  // Create action objects for easier prop passing
  const nodeActions = {
    addEdgeNode: () =>
      NodeManagement.addEdgeNode(
        state.edgeNodes,
        state.edgeCoverage,
        state.setEdgeNodes
      ),
    removeEdgeNode: () =>
      NodeManagement.removeEdgeNode(
        state.edgeNodes,
        state.selectedEdge,
        state.setEdgeNodes,
        state.setSelectedEdge
      ),
    addCentralNode: () =>
      NodeManagement.addCentralNode(
        state.centralNodes,
        state.centralCoverage,
        state.setCentralNodes
      ),
    removeCentralNode: () =>
      NodeManagement.removeCentralNode(
        state.centralNodes,
        state.selectedCentral,
        state.setCentralNodes,
        state.setSelectedCentral
      ),
    deleteSelectedNode: () =>
      NodeManagement.deleteSelectedNode(
        state.selectedEdge,
        state.selectedCentral,
        state.setEdgeNodes,
        state.setCentralNodes,
        state.setSelectedEdge,
        state.setSelectedCentral
      ),
    clearAllUsers: async () =>
      await NodeManagement.clearAllUsers(state.setUsers, state.setSelectedUser),
    resetSimulation: () => {
      NodeManagement.resetSimulation(() => nodeActions.clearEverything());
      // Also reset the simulation data if available
      if (state.simulationData?.resetSimulation) {
        state.simulationData.resetSimulation();
      }
    },
  };

  const userActions = {
    deleteSelectedUser: async () =>
      await UserManagement.deleteSelectedUser(
        state.selectedUser,
        state.setUsers,
        state.setSelectedUser
      ),
    runPlacementAlgorithm: () =>
      runPlacementAlgorithm(
        state.users,
        state.edgeNodes,
        state.placementAlgorithm,
        state.setEdgeNodes,
        state.setUsers
      ),
    runAssignmentAlgorithm: () =>
      runAssignmentAlgorithm(
        state.users,
        state.edgeNodes,
        state.centralNodes,
        state.assignmentAlgorithm,
        state.setUsers
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
          users={state.users}
          setUsers={state.setUsers}
          edgeNodes={state.edgeNodes}
          setEdgeNodes={state.setEdgeNodes}
          centralNodes={state.centralNodes}
          setCentralNodes={state.setCentralNodes}
          totalLatency={state.totalLatency}
          setTotalLatency={state.setTotalLatency}
          selectedUser={state.selectedUser}
          setSelectedUser={state.setSelectedUser}
          selectedEdge={state.selectedEdge}
          setSelectedEdge={state.setSelectedEdge}
          selectedCentral={state.selectedCentral}
          setSelectedCentral={state.setSelectedCentral}
          zoomIn={eventHandlers.zoomIn}
          zoomOut={eventHandlers.zoomOut}
          resetZoom={eventHandlers.resetZoom}
          predictionSteps={state.predictionSteps}
          setPredictionSteps={state.setPredictionSteps}
          edgeCoverage={state.edgeCoverage}
          setEdgeCoverage={state.setEdgeCoverage}
          centralCoverage={state.centralCoverage}
          setCentralCoverage={state.setCentralCoverage}
          autoAssignment={state.autoAssignment}
          setAutoAssignment={state.setAutoAssignment}
          simulationData={state.simulationData}
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
          placementAlgorithm={state.placementAlgorithm}
          setPlacementAlgorithm={state.setPlacementAlgorithm}
          runPlacementAlgorithm={userActions.runPlacementAlgorithm}
          assignmentAlgorithm={state.assignmentAlgorithm}
          setAssignmentAlgorithm={state.setAssignmentAlgorithm}
          runAssignmentAlgorithm={userActions.runAssignmentAlgorithm}
          runGAPAssignment={userActions.runGAPAssignment}
          liveData={state.liveData}
          setLiveData={state.setLiveData}
          roadNetwork={state.roadNetwork}
          setRoadNetwork={state.setRoadNetwork}
          realModeData={state.realModeData}
          setRealModeData={state.setRealModeData}
        />
      </ControlPanel>

      {/* Right Metrics Panel */}
      <MetricsPanel>
        <MetricsPanelContent
          users={state.users}
          edgeNodes={state.edgeNodes}
          centralNodes={state.centralNodes}
          totalLatency={state.totalLatency}
          selectedUser={state.selectedUser}
          setSelectedUser={state.setSelectedUser}
          selectedEdge={state.selectedEdge}
          setSelectedEdge={state.setSelectedEdge}
          selectedCentral={state.selectedCentral}
          setSelectedCentral={state.setSelectedCentral}
          liveData={state.liveData}
          roadNetwork={state.roadNetwork}
        />
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
