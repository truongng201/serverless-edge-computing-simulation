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
  selectedModel,
  setSelectedModel,
  selectedUser,
  selectedEdge,
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
  simulationMode,
  setSimulationMode,
  realModeData,
  setRealModeData
}) {
  const [loadingData, setLoadingData] = useState(false)
  const [dataError, setDataError] = useState("")
  const intervalRef = useRef(null)
  const realModeIntervalRef = useRef(null)
  const transitionTimeoutRef = useRef(null)

    // Function to fetch real cluster status
  const fetchRealClusterStatus = async () => {
    try {
      setLoadingData(true)
      setDataError("")

      // Fetch cluster status and all users in parallel
      const [clusterResponse, usersResponse] = await Promise.all([
        axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/cluster/status`),
        axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_all_users`)
      ])

      if (clusterResponse.data && clusterResponse.data.success) {
        setRealModeData(clusterResponse.data)
        
        
        const realCentralNode = {
          id: clusterResponse.data.central_node.id || "central_node",
          x: clusterResponse.data.central_node.location.x || 600,
          y: clusterResponse.data.central_node.location.y || 400,
          coverage: clusterResponse.data.central_node.coverage || centralCoverage[0] || 500,
          currentLoad: clusterResponse.data.central_node.cpu_usage || 0,
        }

        setCentralNodes([realCentralNode])
        
        const realEdgeNodes = (clusterResponse.data.cluster_info.edge_nodes_info || []).map((node, index) => ({
          id: node.node_id || `edge_${index}`,
          x: node.location.x || 100 + index * 100,
          y: node.location.y || 200 + index * 100,
          coverage: node.coverage || edgeCoverage[0] || 500,
          currentLoad: node.metrics.cpu_usage || 0,
          
        }))
        
        // Always update edge nodes array
        setEdgeNodes(realEdgeNodes)

        // Update users from API response
        if (usersResponse.data && usersResponse.data.success && usersResponse.data.users) {
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
            
          }))
          setUsers(realUsers)
        }
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

  


  useEffect(() => {
    

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (realModeIntervalRef.current) {
        clearInterval(realModeIntervalRef.current);
      }
    };
  }, [isSimulating, simulationSpeed]);

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
                    <div className="mt-1 text-gray-600">
                      📊 View detailed metrics in the right panel →
                      {loadingData && (
                        <span className="ml-1 text-xs text-blue-600">
                          Fetching real data...
                        </span>
                      )}
                    </div>
                  </div>
                  {realModeData && (
                    <div className="mt-2 text-gray-700">
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
            
            {dataError && <div className="text-xs text-red-600">{dataError}</div>}
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
              <Label className="text-xs">Coverage: {centralCoverage[0]}px</Label>
              <Slider value={centralCoverage} onValueChange={setCentralCoverage} max={1000} min={0} step={20} />
            </div>
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
              <Label className="text-xs">Coverage: {edgeCoverage[0]}px</Label>
              <Slider value={edgeCoverage} onValueChange={setEdgeCoverage} max={1000} min={0} step={10} />
            </div>
            
          </CardContent>
        </Card>
      </div>
    </>
  )
}
