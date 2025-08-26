import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Play,
  Pause,
  RotateCcw,
  Users,
  Server,
  Plus,
  Minus,
  Database,
  Trash2,
  Edit3,
  ChevronLeft,
  MapPin,
  Target,
  Navigation,
  
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { generateSaigonRoadNetwork } from "../../lib/road-network";
import { generateStreetMapUsers, convertToStreetMapUsers } from "../../lib/street-map-users";

export default function ControlPanelContent({
  users,
  setUsers,
  edgeNodes,
  setEdgeNodes,
  centralNodes,
  setCentralNodes,
  isSimulating,
  setIsSimulating,
  simulationSpeed,
  setSimulationSpeed,
  predictionEnabled,
  setPredictionEnabled,
  selectedModel,
  setSelectedModel,
  selectedUser,
  selectedEdge,
  setSelectedEdge,
  selectedCentral,
  userSpeed,
  setUserSpeed,
  userSize,
  setUserSize,
  predictionSteps,
  setPredictionSteps,
  edgeCoverage,
  setEdgeCoverage,
  centralCoverage,
  setCentralCoverage,
  zoomLevel,
  editMode,
  setEditMode,
  models,
  deleteSelectedUser,
  resetSimulation,
  addEdgeNode,
  removeEdgeNode,
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
  leftPanelOpen,
  setLeftPanelOpen,
  placementAlgorithm,
  setPlacementAlgorithm,
  maxCoverageDistance,
  setMaxCoverageDistance,
  runPlacementAlgorithm,
  assignmentAlgorithm,
  setAssignmentAlgorithm,
  runAssignmentAlgorithm,
  runGAPAssignment,
  liveData,
  setLiveData,
  roadNetwork,
  setRoadNetwork,
  simulationMode,
  setSimulationMode,
  realModeData,
  setRealModeData,
  selectedScenario,
  setSelectedScenario,
  updateEdgeCoverage,
}) {
  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState("");
  const [simulationLoading, setSimulationLoading] = useState(false);
  const intervalRef = useRef(null);

  // Helper function to clear all users from backend
  const clearAllUsersFromBackend = async () => {
    try {
      if (process.env.NEXT_PUBLIC_API_URL) {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_all_users`, {
          method: 'DELETE'
        });
        
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
    if (typeof runGAPAssignment === 'function') {
      runGAPAssignment(users, edgeNodes, centralNodes, setUsers, {
        method: 'greedy',
        enableMemoryConstraints: false,
        debug: true
      });
    } else {
      console.error("runGAPAssignment not available");
      alert("GAP batch assignment not available. Please use regular assignment.");
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
      const updatedEdgeNodes = edgeNodes.map(node => 
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
      const updatedCentralNodes = centralNodes.map(node => 
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

      console.log("Street map scenario initialized with", streetUsers.length, "users");
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

  // Stop live data polling
  const stopLiveDataPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      // Calculate interval: 1x = 5000ms, 5x = 1000ms
      // Formula: 5000 / simulationSpeed[0]
      const intervalMs = Math.max(1000, 5000 / simulationSpeed[0]);
      realModeIntervalRef.current = setInterval(
        fetchRealClusterStatus,
        intervalMs
      );
    } else {
      // Stop real-time polling
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current);
        realModeIntervalRef.current = null;
      }
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
      intervalRef.current = setInterval(
        refreshClusterAndUsersData,
        intervalMs
      );
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
          console.error("Error fetching updated data after starting simulation:", fetchError);
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
          console.error("Error fetching updated data after stopping simulation:", fetchError);
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
        {/* Edit Mode Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Edit3 className="w-4 h-4" />
              Edit Mode
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Edit Mode</Label>
              <Select value={editMode} onValueChange={setEditMode}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None - Add Users</SelectItem>
                  <SelectItem value="drag">Drag - Pan View</SelectItem>
                  <SelectItem value="nodes">Nodes Only</SelectItem>
                  <SelectItem value="users">Users Only</SelectItem>
                  <SelectItem value="both">Nodes & Users</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {editMode !== "none" && (
              <div className="text-xs text-gray-600 space-y-1">
                {editMode === "drag" ? (
                  <>
                    <div>• Drag to pan the view</div>
                    <div>• Mouse wheel to zoom</div>
                    <div>• Click to select elements</div>
                  </>
                ) : (
                  <>
                <div>• Drag to move elements</div>
                <div>• Click to select elements</div>
                <div>• Dashed rings show editable items</div>
                  </>
                )}
              </div>
            )}
            {(selectedEdge || selectedCentral) && (
              <Button
                onClick={deleteSelectedNode}
                size="sm"
                variant="destructive"
                className="w-full"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Selected Node
              </Button>
            )}
            {selectedUser && (
              <Button
                onClick={deleteSelectedUser}
                size="sm"
                variant="destructive"
                className="w-full"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Selected User
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Clear All Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Clear Controls</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Button onClick={clearAllUsers} size="sm" variant="outline">
                <Users className="w-4 h-4 mr-1" />
                Users
              </Button>
              <Button onClick={clearAllEdgeNodes} size="sm" variant="outline">
                <Server className="w-4 h-4 mr-1" />
                Edges
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={clearAllCentralNodes}
                  size="sm"
                  variant="outline"
                >
                <Database className="w-4 h-4 mr-1" />
                Central
              </Button>
                <Button
                  onClick={clearEverything}
                  size="sm"
                  variant="destructive"
                >
                <Trash2 className="w-4 h-4 mr-1" />
                All
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Node Placement Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Target className="w-4 h-4" />
              Node Placement
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Placement Algorithm</Label>
              <Select
                value={placementAlgorithm}
                onValueChange={setPlacementAlgorithm}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="topk-demand">Top-K Demand</SelectItem>
                  <SelectItem value="kmeans">K-Means Clustering</SelectItem>
                  <SelectItem value="random-random">Random-Random</SelectItem>
                  <SelectItem value="random-nearest">Random-Nearest</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label className="text-xs">
                Max Coverage Distance: {maxCoverageDistance[0]}px
              </Label>
              <Slider 
                value={maxCoverageDistance} 
                onValueChange={setMaxCoverageDistance} 
                max={200} 
                min={50} 
                step={10} 
                className="h-4" 
              />
            </div>
            
            <Button 
              onClick={runPlacementAlgorithm} 
              size="sm" 
              variant="default" 
              className="w-full"
              disabled={!users?.length || !edgeNodes.length}
            >
              <MapPin className="w-4 h-4 mr-1" />
              Run Node Placement
            </Button>
          </CardContent>
        </Card>

        {/* User Assignment Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Target className="w-4 h-4" />
              User Assignment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Assignment Algorithm</Label>
              <Select
                value={assignmentAlgorithm}
                onValueChange={setAssignmentAlgorithm}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="nearest-distance">Nearest Distance</SelectItem>
                  <SelectItem value="nearest-latency">Nearest Latency</SelectItem>
                  <SelectItem value="gap-baseline">GAP Baseline</SelectItem>
                  <SelectItem value="random">Random Assignment</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="text-xs text-gray-600 mb-2">
              <div>Edge Servers: {edgeNodes.length}</div>
              <div>Central Servers: {centralNodes.length}</div>
              <div>Users: {users?.length || 0}</div>
            </div>

            <div className="grid grid-cols-1 gap-2">
              <Button
                onClick={runAssignmentAlgorithm}
                size="sm"
                variant="outline"
                className="w-full"
                disabled={!users?.length || (!edgeNodes.length && !centralNodes.length)}
              >
                <MapPin className="w-4 h-4 mr-1" />
                Run User Assignment
              </Button>
              
              {assignmentAlgorithm === "gap-baseline" && (
                <Button
                  onClick={() => runGAPBatch()}
                  size="sm"
                  variant="default"
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  disabled={!users?.length || (!edgeNodes.length && !centralNodes.length)}
                >
                  <Target className="w-4 h-4 mr-1" />
                  Run GAP Batch (Optimal)
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Live System Status */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Server className="w-4 h-4" />
              Live System Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <div className="text-xs text-green-600 font-medium">
                Live Data - Connected to backend cluster
              </div>

              <div className="bg-green-50 p-2 rounded text-xs">
                <div className="flex items-center justify-between">
                  <span>Status:</span>
                  <Badge variant="default" className="text-xs bg-green-600">
                    Connected
                  </Badge>
                </div>
                <div className="mt-1 text-gray-600">
                  📊 View detailed metrics in the right panel →
                  {loadingData && (
                    <span className="ml-1 text-xs text-blue-600">
                      Fetching live data...
                    </span>
                  )}
                </div>
                {liveData && (
                  <div className="mt-2 text-gray-700">
                    <div>
                      Central CPU:{" "}
                      {liveData.central_node?.cpu_usage?.toFixed(1)}%
                    </div>
                    <div>
                      Edge Nodes: {liveData.edge_nodes?.length || 0}
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={fetchLiveClusterStatus}
                  size="sm"
                  variant="outline"
                  disabled={loadingData}
                  className="text-xs"
                >
                  <Database className="w-3 h-3 mr-1" />
                  Refresh
                </Button>
                
                <Button
                  onClick={startLiveDataPolling}
                  size="sm"
                  variant="default"
                  className="text-xs bg-green-600 hover:bg-green-700"
                >
                  <Play className="w-3 h-3 mr-1" />
                  Auto Poll
                </Button>
              </div>
            </div>

            {dataError && (
              <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                {dataError}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Scenario Selection */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Navigation className="w-4 h-4" />
              Scenario Selection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Scenario</Label>
              <Select
                value={selectedScenario}
                onValueChange={handleScenarioChange}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Self adding user)</SelectItem>
                  <SelectItem value="scenario2">Scenario 2: DACT Sample</SelectItem>
                  <SelectItem value="scenario3">Scenario 3: Vehicle Sample</SelectItem>
                  <SelectItem value="scenario4">Scenario 4: Street Map (Saigon)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="text-xs text-gray-600">
              Select a predefined scenario to load sample data, or choose "None"
              to manually add users.
            </div>
          </CardContent>
        </Card>

        {/* Simulation Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Simulation</CardTitle>
          </CardHeader>
          
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button 
                onClick={handleToggleSimulation}
                variant={isSimulating ? "destructive" : "default"} 
                size="sm" 
                className="flex-1"
                disabled={users?.length === 0 || simulationLoading} // Disable if no users or loading
              >
                {isSimulating ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {simulationLoading
                  ? "Loading..."
                  : isSimulating
                  ? "Stop"
                  : "Start"}
              </Button>
              <Button
                onClick={handleResetSimulation}
                variant="outline"
                size="sm"
                disabled={simulationLoading}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
            {isSimulating && (
              <div className="text-xs text-green-600 font-medium flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                API Simulation Active
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-xs">Speed: {simulationSpeed[0]}x</Label>
              <Slider
                value={simulationSpeed}
                onValueChange={setSimulationSpeed}
                max={5}
                min={0.1}
                step={0.1}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-xs">Prediction</Label>
              <Switch
                checked={predictionEnabled}
                onCheckedChange={setPredictionEnabled}
              />
            </div>
          </CardContent>
        </Card>
      
        {/* Zoom Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Zoom & Pan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button
                onClick={zoomIn}
                size="sm"
                variant="outline"
                className="flex-1"
              >
                <Plus className="w-4 h-4" />
                Zoom In
              </Button>
              <Button
                onClick={zoomOut}
                size="sm"
                variant="outline"
                className="flex-1"
              >
                <Minus className="w-4 h-4" />
                Zoom Out
              </Button>
            </div>
            <Button
              onClick={resetZoom}
              size="sm"
              variant="outline"
              className="w-full"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset View
            </Button>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span>Zoom Level</span>
                <span>{(zoomLevel * 100).toFixed(0)}%</span>
              </div>
              <Progress
                value={((zoomLevel - 0.2) / (5 - 0.2)) * 100}
                className="h-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* Model Selection */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Prediction Model</Label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(models).map(([key, name]) => (
                    <SelectItem key={key} value={key}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">
                Prediction Steps: {predictionSteps[0]}
              </Label>
              <Slider
                value={predictionSteps}
                onValueChange={setPredictionSteps}
                max={20}
                min={5}
                step={1}
              />
            </div>
          </CardContent>
        </Card>

        {/* User Settings */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">User Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Speed: {userSpeed[0]}</Label>
              <Slider
                value={userSpeed}
                onValueChange={setUserSpeed}
                max={10}
                min={0.5}
                step={0.5}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Size: {userSize[0]}</Label>
              <Slider
                value={userSize}
                onValueChange={setUserSize}
                max={15}
                min={5}
                step={1}
              />
            </div>
          </CardContent>
        </Card>

        {/* Central Node Settings */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Database className="w-4 h-4" />
              Central Nodes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {simulationMode !== "real" && (
              <>
                <div className="flex gap-2">
                  <Button
                    onClick={addCentralNode}
                    size="sm"
                    variant="outline"
                    className="flex-1"
                  >
                    <Plus className="w-4 h-4" />
                    Add
                  </Button>
                  <Button
                    onClick={removeCentralNode}
                    size="sm"
                    variant="outline"
                    className="flex-1"
                  >
                    <Minus className="w-4 h-4" />
                    Remove
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">
                    Coverage: {centralCoverage[0]}px
                  </Label>
                  <Slider
                    value={centralCoverage}
                    onValueChange={handleCentralCoverageChange}
                    max={1000}
                    min={0}
                    step={20}
                  />
                </div>
              </>
            )}
            {simulationMode === "real" && (
              <>
                <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
                  Central Node managed by real system
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Edge Node Settings */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Edge Nodes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
                        <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
              Edge Nodes managed by live backend system
            </div>

            <div className="space-y-2">
              <Label className="text-xs">Coverage: {edgeCoverage[0]}px</Label>
              <Slider
                value={edgeCoverage}
                onValueChange={handleEdgeCoverageChange}
                max={1000}
                min={0}
                step={10}
              />
              </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

