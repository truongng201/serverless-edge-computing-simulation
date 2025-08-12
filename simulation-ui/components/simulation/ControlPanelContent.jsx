import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import {
  Play, Pause, RotateCcw, Users, Server, Plus, Minus, Database, Trash2, Link, Unlink, Edit3, Move, ChevronLeft, MapPin, Target, Navigation, Eye, EyeOff, ChevronRight, SkipBack, SkipForward
} from "lucide-react"
import { useState, useEffect, useRef } from "react"
import axios from "axios";

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
  selectedAlgorithm,
  setSelectedAlgorithm,
  selectedUser,
  selectedEdge,
  selectedCentral,
  userSpeed,
  setUserSpeed,
  userSize,
  setUserSize,
  predictionSteps,
  setPredictionSteps,
  edgeCapacity,
  setEdgeCapacity,
  edgeCoverage,
  setEdgeCoverage,
  centralCapacity,
  setCentralCapacity,
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
  simulationData,
  placementAlgorithm,
  setPlacementAlgorithm,
  maxCoverageDistance,
  setMaxCoverageDistance,
  runPlacementAlgorithm,
  roadMode,
  setRoadMode,
  showRoads,
  setShowRoads,
  roads,
  simulationMode,
  setSimulationMode,
  realModeData,
  setRealModeData
}) {
  const [dataType, setDataType] = useState("none")
  const [loadingData, setLoadingData] = useState(false)
  const [dataError, setDataError] = useState("")
  const [currentStep, setCurrentStep] = useState(28800) // Starting step for vehicle data
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [stepProgress, setStepProgress] = useState(0)
  const intervalRef = useRef(null)
  const realModeIntervalRef = useRef(null)
  const transitionTimeoutRef = useRef(null)

    // Function to fetch real cluster status
  const fetchRealClusterStatus = async () => {
    try {
      setLoadingData(true)
      setDataError("")

      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/cluster/status`)

      if (response.data && response.data.success) {
        console.log('Real cluster status:', response.data)
        console.log('Central node CPU usage:', response.data.central_node?.cpu_usage)
        console.log('Edge nodes CPU usage:', response.data.health?.nodes_details?.map(n => n.cpu_usage))
        setRealModeData(response.data)
        
        // Get canvas center for positioning nodes
        const centerX = 600  // Fixed center X
        const centerY = 400  // Fixed center Y
        const realCentralNode = {
          id: "central_node",
          x: centerX,
          y: centerY - 100, // Slightly above center
          capacity: response.data.central_node.container_count || 0,
          coverage: centralCoverage[0] || 150,
          connections: [],
          cpu_usage: response.data.central_node.cpu_usage || 0,
          memory_usage: response.data.central_node.memory_usage || 0,
          active_requests: response.data.central_node.active_requests || 0,
          energy_consumption: response.data.central_node.energy_consumption || 0,
          currentLoad: response.data.central_node.cpu_usage || 0,
          isWarm: true,
          lastAccessTime: Date.now()
        }

        setCentralNodes([realCentralNode])
        console.log(centralNodes)
        
        // Create/Update edge nodes based on real data (always update regardless of conditions)
        const realEdgeNodes = (response.data.health.nodes_details || []).map((node, index) => ({
          id: node.node_id || `edge_${index}`,
          x: centerX + 700 * Math.cos((index * 5 * Math.PI) / Math.max(response.data.health.nodes_details.length, 1)),
          y: centerY + 700 * Math.sin((index * 5 * Math.PI) / Math.max(response.data.health.nodes_details.length, 1)),
          capacity: node.container_count || 0,
          coverage: edgeCoverage[0] || 100,
          connections: [],
          currentLoad: node.cpu_usage * 100 || 0,
          memory_usage: node.memory_usage || 0,
          active_requests: node.active_requests || 0,
          energy_consumption: node.energy_consumption || 0,
          currentLoad: node.cpu_usage || 0,
          lastAccessTime: node.last_seen ? new Date(node.last_seen).getTime() : Date.now(),
          status: node.status || "unhealthy", // Default to unhealthy if not specified
          isWarm: node.status === "healthy", // Only warm if explicitly healthy
          isHealthy: node.status === "healthy",
          lastUpdated: Date.now()
        }))
        
        console.log('Creating edge nodes:', realEdgeNodes)
        // Always update edge nodes array
        setEdgeNodes(realEdgeNodes)
        console.log('Edge nodes state updated')
        
      }
    } catch (error) {
      console.error('Error fetching real cluster status:', error)
      setDataError(`Failed to fetch real data: ${error.message}`)
    } finally {
      setLoadingData(false)
    }
  }

  // Handle simulation mode change
  const handleSimulationModeChange = async (mode) => {
    setSimulationMode(mode)
    
    if (mode === "real") {
      // Fetch initial real data
      await fetchRealClusterStatus()
      
      // Start real-time polling every 5 seconds
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current)
      }
      
      realModeIntervalRef.current = setInterval(fetchRealClusterStatus, 5000)
    } else {
      // Stop real-time polling
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current)
        realModeIntervalRef.current = null
      }
      setRealModeData(null)
    }
  }

  // Generic function to fetch sample data with step
  const fetchSampleData = async (endpoint, step) => {
    try {
      // Start transition effect
      setIsTransitioning(true);
      setStepProgress(0);
      
      // First, immediately clear all users to prevent mixing old and new
      setUsers([]);
      
      const params = { step_id: step };
      
      // Simulate progress for better UX
      setStepProgress(25);
      
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, { params });
      
      setStepProgress(50);
      
      if (!res.data || res.data.status !== "success") {
        throw new Error(`Failed to fetch data from ${endpoint}`);
      }
      
      console.log(`Data from ${endpoint} at step ${step}:`, res.data);
      
      setStepProgress(75);
      
      // Extract user data and ensure it's an array
      let userData = res.data.data;
      if (userData && userData.items) {
        userData = userData.items;
      }
      
      if (!Array.isArray(userData)) {
        console.warn("Expected array but got:", typeof userData, userData);
        userData = [];
      }
      
      // Always process the data, even if empty - this ensures complete replacement
      const processedUsers = userData.map((user, index) => ({
        id: user.id || `user_${step}_${index}`,
        x: Number(user.x) || 0, // Use actual coordinates from backend, default to 0
        y: Number(user.y) || 0, // Use actual coordinates from backend, default to 0
        ...user,
        // Add default properties if missing
        vx: 0, // Set to 0 to prevent frontend movement
        vy: 0, // Set to 0 to prevent frontend movement
        manualConnection: user.manualConnection || false,
        latency: user.latency || 0,
        assignedRoad: user.assignedRoad || null,
        roadDirection: user.roadDirection || 1,
        constrainedToRoad: user.constrainedToRoad || false,
        isBackendControlled: true, // Flag to indicate this user is controlled by backend
        // Add transition properties for smooth animation
        opacity: 0,
        scale: 0.8
      }));
      
      console.log(`Setting ${processedUsers.length} new users from ${endpoint} at step ${step}`);
      
      setStepProgress(100);
      
      // Use setTimeout to ensure the clear operation completes before setting new users
      setTimeout(() => {
        setUsers(processedUsers);
        
        // Animate users in smoothly
        setTimeout(() => {
          setUsers(prev => prev.map(user => ({
            ...user,
            opacity: 1,
            scale: 1
          })));
        }, 50);
        
        // End transition after animation
        if (transitionTimeoutRef.current) {
          clearTimeout(transitionTimeoutRef.current);
        }
        transitionTimeoutRef.current = setTimeout(() => {
          setIsTransitioning(false);
          setStepProgress(0);
        }, 300);
      }, 10);
      
    } catch (err) {
      console.error(`Error fetching from ${endpoint}:`, err);
      setDataError(err.message);
      setIsTransitioning(false);
      setStepProgress(0);
    }
  };
  // API call for DACT sample
  const fetchDACTSample = async () => {
    setLoadingData(true)
    setDataError("")
    try {
      await fetchSampleData("/get_dact_sample", 659);
    } finally {
      setLoadingData(false);
    }
  }

  // API call for Vehicle sample
  const fetchVehicleSample = async () => {
    setLoadingData(true)
    setDataError("")
    try {
      await fetchSampleData("/get_sample", 28800);
    } finally {
      setLoadingData(false);
    }
  }

  // Handle data type change
  const handleDataTypeChange = async (value) => {
    setDataType(value)
    
    // Always clear users first to prevent mixing
    setUsers([]);
    
    // If switching to "none", restore normal user movement
    if (value === "none") {
      // Don't restore any users - let user manually add them
      console.log("Switched to none mode - users cleared");
    } else if (value === "dact") {
      // Clear all existing users first, then load DACT data
      console.log("Loading DACT data...");
      setCurrentStep(659); // Set initial step for DACT
      await fetchDACTSample()
    } else if (value === "vehicle") {
      // Clear all existing users first, then load vehicle data
      console.log("Loading Vehicle data...");
      setCurrentStep(28800); // Set initial step for Vehicle
      await fetchVehicleSample()
    }
    
    // If real mode was active, maintain it after data type change
    if (simulationMode === "real") {
      // Re-initialize real mode to ensure it continues working
      await handleSimulationModeChange("real")
    }
  }

  // Effect to handle simulation intervals
  useEffect(() => {
    if (isSimulating && dataType !== "none") {
      console.log(`Starting simulation for ${dataType} at step ${currentStep}`);
      
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      // Set up interval to fetch data every 1 second with smooth transitions
      intervalRef.current = setInterval(() => {
        setCurrentStep(prevStep => {
          const nextStep = prevStep + 1;
          console.log(`Fetching next step: ${nextStep} (previous was ${prevStep})`);
          
          // Determine endpoint based on dataType
          const endpoint = dataType === "dact" ? "/get_dact_sample" : "/get_sample";
          
          // Use the nextStep directly in the async call to avoid closure issues
          (async () => {
            try {
              await fetchSampleData(endpoint, nextStep);
            } catch (error) {
              console.error(`Error fetching step ${nextStep}:`, error);
            }
          })();
          
          return nextStep;
        });
      }, Math.max(500, 2000 / simulationSpeed[0])); // Adjust interval based on simulation speed, minimum 500ms

    } else {
      console.log("Stopping simulation");
      // Clear interval when simulation stops
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current);
      }
      if (transitionTimeoutRef.current) {
        clearTimeout(transitionTimeoutRef.current);
      }
    };
  }, [isSimulating, dataType, simulationSpeed]);

  // Override resetSimulation to stop intervals
  const handleResetSimulation = () => {
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
    setIsSimulating(false);
    setSimulationMode("demo");
    setRealModeData(null);
    setIsTransitioning(false);
    setStepProgress(0);
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
                  <SelectItem value="nodes">Nodes Only</SelectItem>
                  <SelectItem value="users">Users Only</SelectItem>
                  <SelectItem value="both">Nodes & Users</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {editMode !== "none" && (
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Drag to move elements</div>
                <div>• Click to select elements</div>
                <div>• Dashed rings show editable items</div>
              </div>
            )}
            {(selectedEdge || selectedCentral) && (
              <Button onClick={deleteSelectedNode} size="sm" variant="destructive" className="w-full">
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Selected Node
              </Button>
            )}
            {selectedUser && (
              <Button onClick={deleteSelectedUser} size="sm" variant="destructive" className="w-full">
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
              <Button onClick={clearAllCentralNodes} size="sm" variant="outline">
                <Database className="w-4 h-4 mr-1" />
                Central
              </Button>
              <Button onClick={clearEverything} size="sm" variant="destructive">
                <Trash2 className="w-4 h-4 mr-1" />
                All
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Auto Placement Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Target className="w-4 h-4" />
              Auto Placement
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Algorithm</Label>
              <Select value={placementAlgorithm} onValueChange={setPlacementAlgorithm}>
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
              <Label className="text-xs">Max Coverage Distance: {maxCoverageDistance[0]}px</Label>
              <Slider 
                value={maxCoverageDistance} 
                onValueChange={setMaxCoverageDistance} 
                max={200} 
                min={50} 
                step={10} 
                className="h-4" 
              />
            </div>
            
            <div className="text-xs text-gray-600 mb-2">
              <div>Edge Servers: {edgeNodes.length}</div>
              <div>Users: {users?.length || 0}</div>
            </div>
            
            <Button 
              onClick={runPlacementAlgorithm} 
              size="sm" 
              variant="default" 
              className="w-full"
              disabled={!users?.length || !edgeNodes.length}
            >
              <MapPin className="w-4 h-4 mr-1" />
              Run Placement
            </Button>
          </CardContent>
        </Card>

                
        {/* Data Type Selector */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Database className="w-4 h-4" />
              Select Dataset
              {isTransitioning && (
                <div className="ml-auto">
                  <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                </div>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs flex items-center gap-2">
                <span>Dataset</span>
                {loadingData && !isTransitioning && (
                  <span className="text-xs text-blue-600 flex items-center gap-2">
                    <span className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin"></span>
                    Loading initial data...
                  </span>
                )}
              </Label>
              <Select value={dataType} onValueChange={handleDataTypeChange} disabled={isTransitioning}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (UI/Clicked Data)</SelectItem>
                  <SelectItem value="dact">DACT</SelectItem>
                  <SelectItem value="vehicle">Vehicle</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            
            
            {isTransitioning && (
              <div className="space-y-2">
                <div className="text-xs text-blue-600 flex items-center gap-2">
                  <div className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  Transitioning to step {currentStep}...
                </div>
                {stepProgress > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500">
                      Progress: {Math.round(stepProgress)}%
                    </div>
                    <Progress value={stepProgress} className="h-1" />
                  </div>
                )}
              </div>
            )}
            
            {dataError && (
              <div className="text-xs text-red-600 p-2 bg-red-50 rounded">
                {dataError}
              </div>
            )}
            
            {dataType !== "none" && !loadingData && !isTransitioning && (
              <div className="text-xs text-green-600 p-2 bg-green-50 rounded">
                ✓ Data loaded successfully
              </div>
            )}
          </CardContent>
        </Card>

        {/* Simulation Mode Selector */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Server className="w-4 h-4" />
              Simulation Mode
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Mode</Label>
              <Select value={simulationMode} onValueChange={handleSimulationModeChange}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="demo">Demo Mode</SelectItem>
                  <SelectItem value="real">Real Mode (Live Data)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {simulationMode === "real" && (
              <div className="space-y-2">
                <div className="text-xs text-green-600 font-medium">
                  Real Mode Active - Live data from API
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
                  </div>
                  {realModeData && (
                    <div className="mt-2 text-gray-700">
                      <div>Nodes: {realModeData.health?.healthy_nodes || 0}/{realModeData.health?.total_nodes || 0} healthy</div>
                      <div>Central CPU: {realModeData.central_node?.cpu_usage?.toFixed(1)}%</div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {simulationMode === "demo" && (
              <div className="text-xs text-gray-600">
                Demo mode - manual control of nodes and users
              </div>
            )}
            
            {loadingData && <div className="text-xs text-blue-600">Fetching real data...</div>}
            {dataError && <div className="text-xs text-red-600">{dataError}</div>}
          </CardContent>
        </Card>

        {/* Simulation Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Simulation</CardTitle>
          </CardHeader>
          
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <div className="text-xs text-gray-600">
                Current Step: {currentStep}
              </div>
              <div className="text-xs text-gray-500">
                Data Type: {dataType}
              </div>
              <div className="text-xs text-gray-500">
                Status: {isSimulating ? 'running' : 'stopped'}
                {loadingData && ' (loading...)'}
                {isTransitioning && ' (transitioning...)'}
              </div>
              
              {/* Step Progress Indicator */}
              {isTransitioning && stepProgress > 0 && (
                <div className="space-y-1">
                  <div className="text-xs text-blue-600">
                    Loading step {currentStep + 1}...
                  </div>
                  <Progress value={stepProgress} className="h-2" />
                </div>
              )}
              
              {/* Smooth transition indicator */}
              {isSimulating && dataType !== "none" && (
                <div className="space-y-1">
                  <div className="text-xs text-green-600">
                    ✓ Smooth transitions enabled
                  </div>
                  <div className="text-xs text-gray-500">
                    Interval: {Math.max(500, 2000 / simulationSpeed[0])}ms
                  </div>
                </div>
              )}
              
              {dataError && (
                <div className="text-xs text-red-500">
                  Error: {dataError}
                </div>
              )}
            </div>
           
            {simulationData?.currentStep && (
              <div className="space-y-1">
                <div className="text-xs text-gray-600">
                  Current Timestep: {simulationData.currentStep.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500">
                  Status: {simulationData.simulationStatus || 'stopped'}
                  {simulationData.isLoading && ' (loading...)'}
                </div>
                {simulationData.error && (
                  <div className="text-xs text-red-500">
                    Error: {simulationData.error}
                  </div>
                )}
              </div>
            )}
            {/* Step Controls for Manual Navigation */}
            {dataType !== "none" && (
              <div className="flex gap-2 mt-2">
                <Button 
                  onClick={() => {
                    const newStep = currentStep - 1;
                    setCurrentStep(newStep);
                    const endpoint = dataType === "dact" ? "/get_dact_sample" : "/get_sample";
                    fetchSampleData(endpoint, newStep);
                  }} 
                  size="sm" 
                  variant="outline" 
                  className="flex-1"
                  disabled={loadingData || isTransitioning}
                >
                  <SkipBack className="w-4 h-4 mr-1" />
                  Prev
                </Button>
                <Button 
                  onClick={() => {
                    const newStep = currentStep + 1;
                    setCurrentStep(newStep);
                    const endpoint = dataType === "dact" ? "/get_dact_sample" : "/get_sample";
                    fetchSampleData(endpoint, newStep);
                  }} 
                  size="sm" 
                  variant="outline" 
                  className="flex-1"
                  disabled={loadingData || isTransitioning}
                >
                  <SkipForward className="w-4 h-4 mr-1" />
                  Next
                </Button>
              </div>
            )}
            
            <div className="flex gap-2">
              <Button 
                onClick={() => setIsSimulating(!isSimulating)} 
                variant={isSimulating ? "destructive" : "default"} 
                size="sm" 
                className="flex-1"
                disabled={users?.length === 0} // Disable if no users
              >
                {isSimulating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                {isSimulating ? "Pause" : "Start"}
              </Button>
              <Button onClick={handleResetSimulation} variant="outline" size="sm">
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">
                Speed: {simulationSpeed[0]}x 
                {isSimulating && dataType !== "none" && (
                  <span className="text-blue-600 ml-1">
                    ({Math.max(500, 2000 / simulationSpeed[0])}ms intervals)
                  </span>
                )}
              </Label>
              <Slider value={simulationSpeed} onValueChange={setSimulationSpeed} max={5} min={0.1} step={0.1} />
              <div className="text-xs text-gray-500">
                Higher speed = faster step transitions
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-xs">Prediction</Label>
              <Switch checked={predictionEnabled} onCheckedChange={setPredictionEnabled} />
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
              <Button onClick={zoomIn} size="sm" variant="outline" className="flex-1">
                <Plus className="w-4 h-4" />
                Zoom In
              </Button>
              <Button onClick={zoomOut} size="sm" variant="outline" className="flex-1">
                <Minus className="w-4 h-4" />
                Zoom Out
              </Button>
            </div>
            <Button onClick={resetZoom} size="sm" variant="outline" className="w-full">
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset View
            </Button>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span>Zoom Level</span>
                <span>{(zoomLevel * 100).toFixed(0)}%</span>
              </div>
              <Progress value={((zoomLevel - 0.2) / (5 - 0.2)) * 100} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Algorithm Selection */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Prediction Model</Label>
              <Select value={selectedAlgorithm} onValueChange={setSelectedAlgorithm}>
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
              <Label className="text-xs">Prediction Steps: {predictionSteps[0]}</Label>
              <Slider value={predictionSteps} onValueChange={setPredictionSteps} max={20} min={5} step={1} />
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
              <Slider value={userSpeed} onValueChange={setUserSpeed} max={10} min={0.5} step={0.5} />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Size: {userSize[0]}</Label>
              <Slider value={userSize} onValueChange={setUserSize} max={15} min={5} step={1} />
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
              <div className="flex gap-2">
                <Button onClick={addCentralNode} size="sm" variant="outline" className="flex-1">
                  <Plus className="w-4 h-4" />
                  Add
                </Button>
                <Button onClick={removeCentralNode} size="sm" variant="outline" className="flex-1">
                  <Minus className="w-4 h-4" />
                  Remove
                </Button>
              </div>
            )}
            {simulationMode === "real" && (
              <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
                Central Node managed by real system
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-xs">Capacity: {centralCapacity[0]}</Label>
              <Slider value={centralCapacity} onValueChange={setCentralCapacity} max={1000} min={200} step={50} />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Coverage: {centralCoverage[0]}px</Label>
              <Slider value={centralCoverage} onValueChange={setCentralCoverage} max={300} min={0} step={20} />
            </div>
            {selectedCentral && (
              <div className="p-2 bg-blue-50 rounded text-xs">
                <div>Selected: {selectedCentral.id}</div>
                <div>Position: ({Math.round(selectedCentral.x)}, {Math.round(selectedCentral.y)})</div>
                <div>Capacity: {selectedCentral.capacity}</div>
                <div>Load: {Math.round(selectedCentral.currentLoad)}%</div>
                <div>Coverage: {selectedCentral.coverage}px</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edge Node Settings */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Edge Nodes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {simulationMode !== "real" && (
              <div className="flex gap-2">
                <Button onClick={addEdgeNode} size="sm" variant="outline" className="flex-1">
                  <Plus className="w-4 h-4" />
                  Add
                </Button>
                <Button onClick={removeEdgeNode} size="sm" variant="outline" className="flex-1">
                  <Minus className="w-4 h-4" />
                  Remove
                </Button>
              </div>
            )}
            {simulationMode === "real" && (
              <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
                Edge Nodes managed by real system
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-xs">Capacity: {edgeCapacity[0]}</Label>
              <Slider value={edgeCapacity} onValueChange={setEdgeCapacity} max={200} min={50} step={10} />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Coverage: {edgeCoverage[0]}px</Label>
              <Slider value={edgeCoverage} onValueChange={setEdgeCoverage} max={200} min={0} step={10} />
            </div>
            {selectedEdge && (
              <div className="p-2 bg-green-50 rounded text-xs">
                <div>Selected: {selectedEdge.id}</div>
                <div>Position: ({Math.round(selectedEdge.x)}, {Math.round(selectedEdge.y)})</div>
                <div>Capacity: {selectedEdge.capacity}</div>
                <div>Load: {Math.round(selectedEdge.currentLoad)}%</div>
                <div>Coverage: {selectedEdge.coverage}px</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
