import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import {
  Play, Pause, RotateCcw, Users, Server, Plus, Minus, Database, Trash2, Link, Unlink, Edit3, Move, ChevronLeft
} from "lucide-react"

export default function ControlPanelContent({
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
  autoAssignment,
  setAutoAssignment,
  algorithms,
  connectUserToNode,
  disconnectUser,
  resetAllConnections,
  updateSelectedUser,
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
  setLeftPanelOpen
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

        {/* Manual Connection Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Link className="w-4 h-4" />
              Connection Control
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Auto Assignment</Label>
              <Switch checked={autoAssignment} onCheckedChange={setAutoAssignment} />
            </div>
            {selectedUser && (
              <div className="space-y-3">
                <div className="p-2 bg-gray-50 rounded text-xs">
                  <div className="font-medium mb-1">Selected User: {selectedUser.id}</div>
                  <div>
                    Connected to: {selectedUser.assignedEdge || selectedUser.assignedCentral || (
                      <span className="text-red-500">None</span>
                    )}
                  </div>
                  <div>
                    Connection: <Badge variant={selectedUser.manualConnection ? "default" : "secondary"} className="text-xs">{selectedUser.manualConnection ? "Manual" : "Auto"}</Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Connect to Node:</Label>
                  <Select
                    value=""
                    onValueChange={(value) => {
                      const [nodeType, nodeId] = value.split(":")
                      connectUserToNode(selectedUser.id, nodeId, nodeType)
                    }}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="Choose node..." />
                    </SelectTrigger>
                    <SelectContent>
                      {edgeNodes.map((edge) => (
                        <SelectItem key={`edge:${edge.id}`} value={`edge:${edge.id}`}>
                          🟢 {edge.id} (Load: {Math.round(edge.currentLoad)}%)
                        </SelectItem>
                      ))}
                      {centralNodes.map((central) => (
                        <SelectItem key={`central:${central.id}`} value={`central:${central.id}`}>
                          💎 {central.id} (Load: {Math.round(central.currentLoad)}%)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => disconnectUser(selectedUser.id)} size="sm" variant="outline" className="flex-1">
                    <Unlink className="w-4 h-4 mr-1" />
                    Disconnect
                  </Button>
                </div>
              </div>
            )}
            <Button onClick={resetAllConnections} size="sm" variant="outline" className="w-full">
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset All Connections
            </Button>
          </CardContent>
        </Card>

        {/* User Editor */}
        {selectedUser && (
          <Card className="mb-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Move className="w-4 h-4" />
                User Editor
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-2 bg-blue-50 rounded text-xs">
                <div className="font-medium mb-2">Editing: {selectedUser.id}</div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <Label className="text-xs">X Position</Label>
                    <Input type="number" value={Math.round(selectedUser.x)} onChange={(e) => updateSelectedUser({ x: Number.parseFloat(e.target.value) || 0 })} className="h-6 text-xs" />
                  </div>
                  <div>
                    <Label className="text-xs">Y Position</Label>
                    <Input type="number" value={Math.round(selectedUser.y)} onChange={(e) => updateSelectedUser({ y: Number.parseFloat(e.target.value) || 0 })} className="h-6 text-xs" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <Label className="text-xs">X Velocity</Label>
                    <Input type="number" step="0.1" value={selectedUser.vx.toFixed(1)} onChange={(e) => updateSelectedUser({ vx: Number.parseFloat(e.target.value) || 0 })} className="h-6 text-xs" />
                  </div>
                  <div>
                    <Label className="text-xs">Y Velocity</Label>
                    <Input type="number" step="0.1" value={selectedUser.vy.toFixed(1)} onChange={(e) => updateSelectedUser({ vy: Number.parseFloat(e.target.value) || 0 })} className="h-6 text-xs" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Size: {selectedUser.size}</Label>
                  <Slider value={[selectedUser.size]} onValueChange={([value]) => updateSelectedUser({ size: value })} max={20} min={5} step={1} className="h-4" />
                </div>
                <div className="mt-2 text-xs text-gray-600">
                  <div>Latency: {selectedUser.latency}ms</div>
                  <div>Edge: {selectedUser.assignedEdge || "None"}</div>
                  <div>Central: {selectedUser.assignedCentral || "None"}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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

        {/* Simulation Controls */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Simulation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
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
            <CardTitle className="text-sm">Algorithm</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Prediction Algorithm</Label>
              <Select value={selectedAlgorithm} onValueChange={setSelectedAlgorithm}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(algorithms).map(([key, name]) => (
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
