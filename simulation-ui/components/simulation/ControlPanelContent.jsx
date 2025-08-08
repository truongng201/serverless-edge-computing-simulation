import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import {
  Play, Pause, RotateCcw, Users, Server, Plus, Minus, Database, Trash2, Link, Unlink, Edit3, Move, ChevronLeft, MapPin, Target, Navigation, Eye, EyeOff
} from "lucide-react"

export default function ControlPanelContent({
  users,
  edgeNodes,
  centralNodes,
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
  roads
}) {
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

        {/* Road Network Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Navigation className="w-4 h-4" />
              Road Network
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Road Mode</Label>
              <Switch checked={roadMode} onCheckedChange={setRoadMode} />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-xs">Show Roads</Label>
              <Switch checked={showRoads} onCheckedChange={setShowRoads} />
            </div>
            
            <div className="text-xs text-gray-600 space-y-1">
              <div>Available Roads: {roads?.length || 0}</div>
              <div>Road Types: Highway, Main, Local</div>
              {roadMode && (
                <div className="text-blue-600 font-medium">
                  Click near roads to place users
                </div>
              )}
            </div>
            
            <div className="bg-blue-50 p-2 rounded text-xs">
              <div className="font-medium mb-1">Road Mode Features:</div>
              <div>• Users snap to nearest road</div>
              <div>• Constrained movement along roads</div>
              <div>• Bidirectional traffic</div>
              <div>• Auto direction reversal</div>
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

        {/* Simulation Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Simulation</CardTitle>
          </CardHeader>
          
          <CardContent className="space-y-3">
           
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
            <div className="flex gap-2">
              <Button onClick={() => setIsSimulating(!isSimulating)} variant={isSimulating ? "destructive" : "default"} size="sm" className="flex-1">
                {isSimulating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                {isSimulating ? "Pause" : "Start"}
              </Button>
              <Button onClick={resetSimulation} variant="outline" size="sm">
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Speed: {simulationSpeed[0]}x</Label>
              <Slider value={simulationSpeed} onValueChange={setSimulationSpeed} max={5} min={0.1} step={0.1} />
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
