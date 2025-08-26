import {
  EdgeNodeSettingsCard,
  CentralNodeSettingsCard,
  UserSettingsCard,
  EditModeCard,
  ClearControlsCard,
  SimulationControlsCard,
  NodePlacementCard,
  UserAssignmentCard,
  LiveSystemStatusCard,
  ScenarioSelectionCard,
  ZoomControlsCard,
  ModelSelectionCard,
} from "./control-cards/ControlCards";
import { ChevronLeft } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { generateSaigonRoadNetwork } from "../../lib/road-network";
import { generateStreetMapUsers } from "../../lib/street-map-users";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function ControlPanelContent({
  users,
  setUsers,
  edgeNodes,
  setEdgeNodes,
  centralNodes,
  setCentralNodes,
  selectedUser,
  selectedEdge,
  setSelectedEdge,
  selectedCentral,
  edgeCoverage,
  setEdgeCoverage,
  centralCoverage,
  setCentralCoverage,
  deleteSelectedUser,
  resetSimulation,
  addCentralNode,
  removeCentralNode,
  deleteSelectedNode,
  clearAllUsers,
  clearAllEdgeNodes,
  clearAllCentralNodes,
  clearEverything,
  zoomIn,
  zoomOut,
  resetZoom,
  placementAlgorithm,
  setPlacementAlgorithm,
  runPlacementAlgorithm,
  assignmentAlgorithm,
  setAssignmentAlgorithm,
  runAssignmentAlgorithm,
  runGAPAssignment,
  simulationMode,
  setRealModeData,
  updateEdgeCoverage,
}) {
  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState("");
  const [simulationLoading, setSimulationLoading] = useState(false);
  const intervalRef = useRef(null);
  const realModeIntervalRef = useRef(null);
  const {
    userSpeed,
    userSize,
    leftPanelOpen,
    setLeftPanelOpen,
    isSimulating,
    setIsSimulating,
    setSelectedScenario,
    simulationSpeed,
    setLiveData,
    setRoadNetwork
  } = useSimulationStore();

  // Helper function to clear all users from backend
  const clearAllUsersFromBackend = async () => {
    try {
      if (process.env.NEXT_PUBLIC_API_URL) {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_all_users`,
          {
            method: "DELETE",
          }
        );

        if (response.ok) {
          console.log("All users cleared from backend");
        } else {
          console.warn("Failed to clear users from backend:", response.status);
        }
      }
    } catch (error) {
      console.error("Error clearing users from backend:", error);
    }
  };

  // Function to run GAP batch assignment
  const runGAPBatch = () => {
    if (typeof runGAPAssignment === "function") {
      runGAPAssignment(users, edgeNodes, centralNodes, setUsers, {
        method: "greedy",
        enableMemoryConstraints: false,
        debug: true,
      });
    } else {
      console.error("runGAPAssignment not available");
      alert(
        "GAP batch assignment not available. Please use regular assignment."
      );
    }
  };

  // Update coverage slider when selected edge changes
  useEffect(() => {
    if (selectedEdge && selectedEdge.coverage !== undefined) {
      setEdgeCoverage([selectedEdge.coverage]);
    }
  }, [selectedEdge, setEdgeCoverage]);

  // Update coverage slider when selected central changes
  useEffect(() => {
    if (selectedCentral && selectedCentral.coverage !== undefined) {
      setCentralCoverage([selectedCentral.coverage]);
    }
  }, [selectedCentral, setCentralCoverage]);

  // Handle edge coverage change
  const handleEdgeCoverageChange = async (newCoverage) => {
    // Update the slider state
    setEdgeCoverage(newCoverage);

    // If an edge is selected, update the local edge node coverage and call the API
    if (selectedEdge) {
      // Update the local edge node coverage
      const updatedEdgeNodes = edgeNodes.map((node) =>
        node.id === selectedEdge.id
          ? { ...node, coverage: newCoverage[0] }
          : node
      );
      setEdgeNodes(updatedEdgeNodes);

      // Update the selected edge with new coverage
      setSelectedEdge({ ...selectedEdge, coverage: newCoverage[0] });

      // Call the API to update the backend if the function is available
      if (updateEdgeCoverage) {
        await updateEdgeCoverage(selectedEdge.id, newCoverage[0]);
      }
    }
  };

  // Handle central coverage change
  const handleCentralCoverageChange = async (newCoverage) => {
    // Update the slider state
    setCentralCoverage(newCoverage);

    // If a central node is selected, update the local central node coverage
    if (selectedCentral) {
      // Update the local central node coverage
      const updatedCentralNodes = centralNodes.map((node) =>
        node.id === selectedCentral.id
          ? { ...node, coverage: newCoverage[0] }
          : node
      );
      setCentralNodes(updatedCentralNodes);

      // Update the selected central with new coverage
      setSelectedCentral({ ...selectedCentral, coverage: newCoverage[0] });

      // Note: Add API call here when central node coverage update API is available
      // if (updateCentralCoverage) {
      //   await updateCentralCoverage(selectedCentral.id, newCoverage[0]);
      // }
    }
  };

  // Function to fetch DACT sample data
  const fetchDACTSample = async () => {
    try {
      setLoadingData(true);
      setDataError("");

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_dact_sample`
      );

      if (response.data && response.data.success && response.data.users) {
        const dactUsers = response.data.users.map((user, index) => ({
          id: user.user_id || `dact_user_${index}`,
          x: user.location.x || Math.random() * 800,
          y: user.location.y || Math.random() * 600,
          vx: 0,
          vy: 0,
          assignedEdge: user.assigned_edge || null,
          assignedCentral: user.assigned_central || null,
          assignedNodeID: user.assigned_node_id || null,
          latency: user.latency || 0,
          size: user.size || userSize[0] || 10,
          last_executed_period: user.last_executed_period || null,
        }));
        setUsers(dactUsers);
      }
    } catch (error) {
      console.error("Error fetching DACT sample data:", error);
      setDataError(`Failed to fetch DACT sample: ${error.message}`);
    } finally {
      setLoadingData(false);
    }
  };

  // Function to fetch Vehicle sample data
  const fetchVehicleSample = async () => {
    try {
      setLoadingData(true);
      setDataError("");

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_vehicles_sample`
      );

      if (response.data && response.data.success && response.data.users) {
        const vehicleUsers = response.data.users.map((user, index) => ({
          id: user.user_id || `vehicle_user_${index}`,
          x: user.location.x || Math.random() * 800,
          y: user.location.y || Math.random() * 600,
          vx: 0,
          vy: 0,
          assignedEdge: user.assigned_edge || null,
          assignedCentral: user.assigned_central || null,
          assignedNodeID: user.assigned_node_id || null,
          latency: user.latency || 0,
          size: user.size || userSize[0] || 10,
          last_executed_period: user.last_executed_period || null,
        }));
        setUsers(vehicleUsers);
      }
    } catch (error) {
      console.error("Error fetching Vehicle sample data:", error);
      setDataError(`Failed to fetch Vehicle sample: ${error.message}`);
    } finally {
      setLoadingData(false);
    }
  };

  // Function to initialize Street Map scenario
  const initializeStreetMapScenario = async () => {
    try {
      setLoadingData(true);
      setDataError("");

      // Clear existing users from backend first
      await clearAllUsersFromBackend();

      // Generate Saigon road network
      const newRoadNetwork = generateSaigonRoadNetwork(1200, 800); // Adjust to canvas size
      setRoadNetwork(newRoadNetwork);

      // Generate initial street map users
      const streetUsers = generateStreetMapUsers(
        newRoadNetwork,
        8, // initial user count (reduced for better performance)
        userSpeed[0],
        userSize[0]
      );
      setUsers(streetUsers);

      console.log(
        "Street map scenario initialized with",
        streetUsers.length,
        "users"
      );
    } catch (error) {
      console.error("Error initializing street map scenario:", error);
      setDataError(`Failed to initialize street map: ${error.message}`);
    } finally {
      setLoadingData(false);
    }
  };

  // Function to fetch live cluster status
  const fetchLiveClusterStatus = async () => {
    try {
      setLoadingData(true);
      setDataError("");

      // Fetch cluster status and all users in parallel
      const [clusterResponse, usersResponse] = await Promise.all([
        axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/cluster/status`
        ),
        axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_all_users`
        ),
      ]);

      if (clusterResponse.data && clusterResponse.data.success) {
        setLiveData(clusterResponse.data);

        const realCentralNode = {
          id: clusterResponse.data.central_node.id || "central_node",
          x: clusterResponse.data.central_node.location.x || 600,
          y: clusterResponse.data.central_node.location.y || 400,
          coverage:
            clusterResponse.data.central_node.coverage || centralCoverage[0],
          currentLoad: clusterResponse.data.central_node.cpu_usage || 0,
        };

        setCentralNodes([realCentralNode]);

        const realEdgeNodes = (
          clusterResponse.data.cluster_info.edge_nodes_info || []
        ).map((node, index) => ({
          id: node.node_id || `edge_${index}`,
          x: node.location.x || 100 + index * 100,
          y: node.location.y || 200 + index * 100,
          coverage: node.coverage || edgeCoverage[0],
          currentLoad: node.metrics.cpu_usage || 0,
        }));

        // Always update edge nodes array
        setEdgeNodes(realEdgeNodes);

        // Update users from API response
        if (
          usersResponse.data &&
          usersResponse.data.success &&
          usersResponse.data.users
        ) {
          const realUsers = usersResponse.data.users.map((user, index) => ({
            id: user.user_id || `user_${index}`,
            x: user.location.x || 0,
            y: user.location.y || 0,
            vx: 0,
            vy: 0,
            assignedEdge: user.assigned_edge || null,
            assignedCentral: user.assigned_central || null,
            assignedNodeID: user.assigned_node_id || null,
            latency: user.latency || 0,
            size: user.size || userSize[0] || 10,
            last_executed_period: user.last_executed_period || null,
          }));
          setUsers(realUsers);
        }
      }
    } catch (error) {
      console.error("Error fetching real cluster status:", error);
      setDataError(`Failed to fetch real data: ${error.message}`);
    } finally {
      setLoadingData(false);
    }
  };

  // Function to refresh users and cluster data - can be used regardless of simulation mode
  const refreshClusterAndUsersData = async () => {
    try {
      // Fetch both cluster status and all users
      const [clusterResponse, usersResponse] = await Promise.all([
        axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/cluster/status`
        ),
        axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_all_users`
        ),
      ]);

      // Update cluster info if available
      if (clusterResponse.data && clusterResponse.data.success) {
        // Update real mode data for metrics display
        setRealModeData(clusterResponse.data);

        // Update central nodes
        const realCentralNode = {
          id: clusterResponse.data.central_node.id || "central_node",
          x: clusterResponse.data.central_node.location.x || 600,
          y: clusterResponse.data.central_node.location.y || 400,
          coverage:
            clusterResponse.data.central_node.coverage || centralCoverage[0],
          currentLoad: clusterResponse.data.central_node.cpu_usage || 0,
        };
        setCentralNodes([realCentralNode]);

        // Update edge nodes
        const realEdgeNodes = (
          clusterResponse.data.cluster_info.edge_nodes_info || []
        ).map((node, index) => ({
          id: node.node_id || `edge_${index}`,
          x: node.location.x || 100 + index * 100,
          y: node.location.y || 200 + index * 100,
          coverage: node.coverage || edgeCoverage[0],
          currentLoad: node.metrics.cpu_usage || 0,
        }));
        setEdgeNodes(realEdgeNodes);
      }

      // Update users if available
      if (
        usersResponse.data &&
        usersResponse.data.success &&
        usersResponse.data.users
      ) {
        const realUsers = usersResponse.data.users.map((user, index) => ({
          id: user.user_id || `user_${index}`,
          x: user.location.x || 0,
          y: user.location.y || 0,
          vx: 0,
          vy: 0,
          assignedEdge: user.assigned_edge || null,
          assignedCentral: user.assigned_central || null,
          assignedNodeID: user.assigned_node_id || null,
          latency: user.latency || 0,
          size: user.size || userSize[0] || 10,
          last_executed_period: user.last_executed_period || null,
        }));
        setUsers(realUsers);
      }
    } catch (error) {
      console.error("Error refreshing cluster and users data:", error);
      // Don't throw error to avoid breaking the calling function
    }
  };

  // Handle scenario selection change
  const handleScenarioChange = async (scenario) => {
    setSelectedScenario(scenario);

    if (scenario === "scenario2") {
      // Load DACT sample data
      await fetchDACTSample();
    } else if (scenario === "scenario3") {
      // Load Vehicle sample data
      await fetchVehicleSample();
    } else if (scenario === "scenario4") {
      // Load Street Map scenario
      await initializeStreetMapScenario();
    } else if (scenario === "none") {
      // Clear users for manual adding and from backend
      await clearAllUsersFromBackend();
      clearAllUsers();
      setRoadNetwork(null); // Clear road network
    }
  };

  // Start live data polling
  const startLiveDataPolling = async () => {
    // Fetch initial data
    await fetchLiveClusterStatus();

    // Start real-time polling with interval based on simulation speed
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Calculate interval: 1x = 5000ms, 5x = 1000ms
    const intervalMs = Math.max(1000, 5000 / simulationSpeed[0]);
    intervalRef.current = setInterval(fetchLiveClusterStatus, intervalMs);
  };

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Handle simulation speed changes in real mode - this should run continuously when in real mode
  useEffect(() => {
    if (simulationMode === "real") {
      // Clear any existing interval first
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current);
      }

      // Set up new interval for real mode - this runs regardless of simulation state
      const intervalMs = Math.max(1000, 5000 / simulationSpeed[0]);
      realModeIntervalRef.current = setInterval(
        fetchRealClusterStatus,
        intervalMs
      );
    } else if (realModeIntervalRef.current) {
      // Only clear interval if we're switching away from real mode
      clearInterval(realModeIntervalRef.current);
      realModeIntervalRef.current = null;
    }
  }, [simulationSpeed]);

  // Handle simulation state changes - start/stop data polling when simulation starts/stops
  useEffect(() => {
    if (isSimulating && simulationMode !== "real") {
      // Start polling for simulation updates when simulation is running (but not in real mode)
      // Real mode has its own polling mechanism above
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      // Calculate interval based on simulation speed
      const intervalMs = Math.max(1000, 3000 / simulationSpeed[0]);
      intervalRef.current = setInterval(refreshClusterAndUsersData, intervalMs);
    } else if (!isSimulating && intervalRef.current) {
      // Stop polling when simulation stops
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [isSimulating, simulationSpeed, simulationMode]);

  // Function to start simulation via API
  const handleStartSimulation = async () => {
    try {
      setDataError(""); // Clear any previous errors
      setSimulationLoading(true);

      // Start the simulation via API
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_simulation`
      );

      if (response.data && response.data.success) {
        setIsSimulating(true);

        // After starting simulation, refresh the cluster status and users data
        // This ensures the UI shows the latest user assignments and cluster info
        try {
          await refreshClusterAndUsersData();
        } catch (fetchError) {
          console.error(
            "Error fetching updated data after starting simulation:",
            fetchError
          );
          // Don't fail the entire operation if data fetch fails
        }
      }
    } catch (error) {
      console.error("Error starting simulation:", error);
      setDataError(`Failed to start simulation: ${error.message}`);
    } finally {
      setSimulationLoading(false);
    }
  };

  // Function to stop simulation via API
  const handleStopSimulation = async () => {
    try {
      setDataError(""); // Clear any previous errors
      setSimulationLoading(true);
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/stop_simulation`
      );
      if (response.data && response.data.success) {
        setIsSimulating(false);

        // After stopping simulation, refresh the cluster status and users data
        // This ensures the UI shows the latest state after stopping
        try {
          await refreshClusterAndUsersData();
        } catch (fetchError) {
          console.error(
            "Error fetching updated data after stopping simulation:",
            fetchError
          );
          // Don't fail the entire operation if data fetch fails
        }
      }
    } catch (error) {
      console.error("Error stopping simulation:", error);
      setDataError(`Failed to stop simulation: ${error.message}`);
    } finally {
      setSimulationLoading(false);
    }
  };

  // Function to handle start/stop simulation button click
  const handleToggleSimulation = async () => {
    if (isSimulating) {
      await handleStopSimulation();
    } else {
      await handleStartSimulation();
    }
  };

  // Override resetSimulation to stop intervals and API simulation
  const handleResetSimulation = async () => {
    // First, stop any running simulation via API
    if (isSimulating) {
      try {
        await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/stop_simulation`);
      } catch (error) {
        console.error("Error stopping simulation during reset:", error);
      }
    }

    // Clean up intervals
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (realModeIntervalRef.current) {
      clearInterval(realModeIntervalRef.current);
      realModeIntervalRef.current = null;
    }
    if (transitionTimeoutRef.current) {
      clearTimeout(transitionTimeoutRef.current);
      transitionTimeoutRef.current = null;
    }

    // Reset states
    setIsSimulating(false);
    setLiveData(null);
    setDataError("");
    setSimulationLoading(false);
    resetSimulation();
  };
  return (
    <>
      {/* Close panel - small left arrow button at the very top, outside all cards */}
      <div className="relative w-full">
        <button
          onClick={() => setLeftPanelOpen && setLeftPanelOpen(!leftPanelOpen)}
          className="absolute right-2 z-30 p-1 rounded hover:bg-gray-200 focus:outline-none"
          aria-label="Close panel"
          type="button"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      </div>
      <div className="pt-8">
        <EditModeCard
          selectedEdge={selectedEdge}
          selectedCentral={selectedCentral}
          selectedUser={selectedUser}
          deleteSelectedNode={deleteSelectedNode}
          deleteSelectedUser={deleteSelectedUser}
        />

        <ClearControlsCard
          clearAllUsers={clearAllUsers}
          clearAllEdgeNodes={clearAllEdgeNodes}
          clearAllCentralNodes={clearAllCentralNodes}
          clearEverything={clearEverything}
        />

        <NodePlacementCard
          placementAlgorithm={placementAlgorithm}
          setPlacementAlgorithm={setPlacementAlgorithm}
          runPlacementAlgorithm={runPlacementAlgorithm}
          users={users}
          edgeNodes={edgeNodes}
        />

        <UserAssignmentCard
          assignmentAlgorithm={assignmentAlgorithm}
          setAssignmentAlgorithm={setAssignmentAlgorithm}
          runAssignmentAlgorithm={runAssignmentAlgorithm}
          runGAPBatch={runGAPBatch}
          users={users}
          edgeNodes={edgeNodes}
          centralNodes={centralNodes}
        />

        <LiveSystemStatusCard
          loadingData={loadingData}
          dataError={dataError}
          fetchLiveClusterStatus={fetchLiveClusterStatus}
          startLiveDataPolling={startLiveDataPolling}
        />

        <ScenarioSelectionCard handleScenarioChange={handleScenarioChange} />

        <SimulationControlsCard
          handleToggleSimulation={handleToggleSimulation}
          handleResetSimulation={handleResetSimulation}
          users={users}
          simulationLoading={simulationLoading}
        />

        <ZoomControlsCard
          zoomIn={zoomIn}
          zoomOut={zoomOut}
          resetZoom={resetZoom}
        />

        <ModelSelectionCard />

        <UserSettingsCard />

        <CentralNodeSettingsCard
          simulationMode={simulationMode}
          addCentralNode={addCentralNode}
          removeCentralNode={removeCentralNode}
          centralCoverage={centralCoverage}
          handleCentralCoverageChange={handleCentralCoverageChange}
        />

        <EdgeNodeSettingsCard
          edgeCoverage={edgeCoverage}
          handleEdgeCoverageChange={handleEdgeCoverageChange}
        />
      </div>
    </>
  );
}
