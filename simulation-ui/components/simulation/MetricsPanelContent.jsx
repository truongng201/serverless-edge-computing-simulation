import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Database, Timer, Users, Link, Server, ChevronRight } from "lucide-react"

export default function MetricsPanelContent({
  users,
  edgeNodes,
  centralNodes,
  totalLatency,
  selectedUser,
  setSelectedUser,
  selectedEdge,
  setSelectedEdge,
  selectedCentral,
  setSelectedCentral,
  models,
  selectedModel,
  setSelectedModel,
  rightPanelOpen,
  setRightPanelOpen,
  simulationMode,
  realModeData,
}) {
  return (
    <>
      {/* Close panel - small right arrow button at the very top, outside all cards */}
      <div className="relative w-full">
        <button
          onClick={() => setRightPanelOpen && setRightPanelOpen(!rightPanelOpen)}
          className="absolute left-2 z-30 p-1 rounded hover:bg-gray-200 focus:outline-none"
          aria-label="Close panel"
          type="button"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      <div className="pt-8">
        {/* System Metrics */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">System Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                Users
              </span>
              <Badge variant="outline">{users.length}</Badge>
            </div>
           
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <Timer className="w-4 h-4" />
                Average Load
              </span>
              <Badge variant={realModeData?.cluster_info?.average_load > 90 ? "destructive" : realModeData?.cluster_info?.average_load > 70 ? "secondary" : "default"}>
                {Math.round(realModeData?.cluster_info?.average_load, 2) ? Math.round(realModeData?.cluster_info?.average_load, 2) : 0}%
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span>Network Load</span>
                <span>0%</span>
              </div>
              <Progress value={0} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Real-Time Metrics for Real Mode */}
        {simulationMode === "real" && realModeData && (
          <Card className="mb-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Server className="w-4 h-4 text-green-600" />
                Live System Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Central Node Metrics */}
              <div className="bg-blue-50 p-3 rounded">
                <div className="font-medium text-blue-800 mb-2 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Central Node
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span>CPU ({realModeData.central_node?.system_info?.cpu_cores_physical} cores):</span>
                    <span className="font-medium">{realModeData.central_node?.cpu_usage?.toFixed(1)}%</span>
                  </div>
                  <Progress value={realModeData.central_node?.cpu_usage || 0} className="h-2" />
                  
                  <div className="flex justify-between">
                    <span>Memory ({realModeData.central_node?.system_info?.memory_total} GB):</span>
                    <span className="font-medium">{realModeData.central_node?.memory_usage?.toFixed(1)}%</span>
                  </div>
                  <Progress value={realModeData.central_node?.memory_usage || 0} className="h-2" />
                  
                  <div className="flex justify-between">
                    <span>Active Requests:</span>
                    <Badge variant="outline" className="text-xs">
                      {realModeData.central_node?.active_requests || 0}
                    </Badge>
                  </div>

                  <div className="flex justify-between">
                    <span>Total Requests:</span>
                    <Badge variant="outline" className="text-xs">
                      {realModeData.central_node?.total_requests || 0}
                    </Badge>
                  </div>
                  
                  <div className="flex justify-between">
                    <span>Warm containers:</span>
                    <Badge variant="outline" className="text-xs">
                      {realModeData.central_node?.warm_container || 0}
                    </Badge>
                  </div>

                  <div className="flex justify-between">
                    <span>Running containers:</span>
                    <Badge variant="outline" className="text-xs">
                      {realModeData.central_node?.running_container || 0}
                    </Badge>
                  </div>
                </div>
              </div>
              
              {/* Edge Nodes Summary */}
              <div className="bg-green-50 p-3 rounded">
                <div className="font-medium text-green-800 mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  Edge Nodes Overview
                </div>
                <div className="text-center">
                    <div className="font-medium text-lg">{realModeData.cluster_info?.total_nodes || 0}</div>
                    <div className="text-gray-600">Total</div>
                  </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="text-center">
                    <div className="font-medium text-lg text-green-600">{realModeData.cluster_info?.healthy_node_count || 0}</div>
                    <div className="text-gray-600">Healthy</div>
                  </div>

                  <div className="text-center">
                    <div className="font-medium text-lg text-yellow-600">{realModeData.cluster_info?.warning_node_count || 0}</div>
                    <div className="text-gray-600">Warning</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium text-lg text-red-600">{realModeData.cluster_info?.unhealthy_node_count || 0}</div>
                    <div className="text-gray-600">Unhealthy</div>
                  </div>
                </div>
              </div>
              
              {/* Individual Edge Node Status */}
              <div className="space-y-2">
                <div className="font-medium text-sm text-gray-700">Individual Node Status</div>
                {realModeData.cluster_info?.edge_nodes_info?.map((node, index) => (
                  <div key={node.node_id} className={`p-2 rounded border text-xs ${
                    node.status === 'healthy'
                      ? 'bg-green-50 border-green-200'
                      : node.status === 'warning'
                        ? 'bg-yellow-50 border-yellow-200'
                        : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="flex justify-between items-center mb-1">
                      <div className={`font-medium ${
                        node.status === 'healthy' 
                          ? 'text-green-800' 
                          : node.status === 'warning'
                            ? 'text-yellow-800'
                            : 'text-red-800'
                      }`}>
                        {node.node_id}
                      </div>
                      <Badge variant={
                        node.status === 'healthy' 
                          ? 'default' 
                          : node.status === 'warning'
                            ? 'success'
                            : 'destructive'
                      } className="text-xs">
                        {node.status}
                      </Badge>
                    </div>
                    
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span>CPU ({node.system_info?.cpu_cores_physical} cores):</span>
                        <span className="font-medium">{(node.metrics.cpu_usage).toFixed(1)}%</span>
                      </div>
                      <Progress value={node.metrics.cpu_usage} className="h-1" />
                      
                      <div className="flex justify-between">
                        <span>Memory ({node.system_info?.memory_total} GB):</span>
                        <span className="font-medium">{(node.metrics.memory_usage).toFixed(1)}%</span>
                      </div>
                      <Progress value={node.metrics.memory_usage} className="h-1" />

                      <div className="flex justify-between">
                        <span>Last seen:</span>
                        <span className="font-medium">{node.last_seen?.toFixed(1)}s ago</span>
                      </div>
                      
                      <div className="flex justify-between">
                        <span>Active requests:</span>
                        <Badge variant="outline" className="text-xs">
                          {node.metrics.active_requests || 0}
                        </Badge>
                      </div>

                      <div className="flex justify-between">
                        <span>Total requests:</span>
                        <Badge variant="outline" className="text-xs">
                          {node.metrics.total_requests || 0}
                        </Badge>
                      </div>

                      <div className="flex justify-between">
                        <span>Warm Container:</span>
                        <Badge variant="outline" className="text-xs">
                          {node.metrics.warm_container || 0}
                        </Badge>
                      </div>

                      <div className="flex justify-between">
                        <span>Running Container:</span>
                        <Badge variant="outline" className="text-xs">
                          {node.metrics.running_container || 0}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Connection Status */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Connection Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {users.map((user) => (
              <div
                key={user.id}
                className={`p-2 rounded cursor-pointer transition-colors text-xs ${
                  selectedUser && selectedUser.id === user.id ? "bg-purple-100" : "hover:bg-gray-50"
                }`}
                onClick={() => setSelectedUser(selectedUser && selectedUser.id === user.id ? null : user)}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="flex items-center gap-1">
                    <div
                      className={`w-2 h-2 rounded-full ${user.manualConnection ? "bg-orange-500" : "bg-blue-500"}`}
                    />
                    {user.id}
                  </span>
                  <Badge variant={user.manualConnection ? "default" : "secondary"} className="text-xs">
                    {user.manualConnection ? "Manual" : "Auto"}
                  </Badge>
                </div>
                <div className="text-gray-600">→ {user.assignedEdge || user.assignedCentral || "Disconnected"}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        

        {/* Latency Breakdown - Show detailed metrics for selected node */}
          <Card className="mb-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Timer className="w-4 h-4" />
                Latency Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(() => {
                const node = selectedEdge || selectedCentral;
                const metrics = node?.lastMetrics;
                const nodeType = selectedEdge ? "Cloudlet" : "Cloud";
                
                return (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-700">{node?.id} ({nodeType})</div>
                    
                    {/* Service Status */}
                    <div className="flex justify-between text-xs">
                      <span>Service Status:</span>
                      <Badge variant={metrics?.isWarmStart ? "default" : "secondary"} className="text-xs">
                        {metrics?.isWarmStart ? "Warm Start" : "Cold Start"}
                      </Badge>
                    </div>
                    
                    {/* Data Size */}
                    <div className="flex justify-between text-xs">
                      <span>Data Size s(u,t):</span>
                      <span className="font-mono">{metrics?.dataSize} MB</span>
                    </div>
                    
                    {/* Communication Delay */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>Communication d_com:</span>
                        <span className="font-mono">{metrics?.communicationDelay} ms</span>
                      </div>
                      <div className="ml-2 text-xs text-gray-500">
                        τ = {metrics?.unitTransmissionDelay} ms/MB
                      </div>
                    </div>
                    
                    {/* Processing Delay */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>Processing d_proc:</span>
                        <span className="font-mono">{metrics?.processingDelay} ms</span>
                      </div>
                      <div className="ml-2 text-xs text-gray-500">
                        ρ = {metrics?.unitProcessingTime} ms/MB
                      </div>
                    </div>
                    
                    {/* Total Latency */}
                    <div className="border-t pt-2">
                      <div className="flex justify-between text-xs font-medium">
                        <span>Total D(u,v,t):</span>
                        <span className="font-mono">{(metrics?.communicationDelay || 0) + (metrics?.processingDelay || 0)} ms</span>
                      </div>
                    </div>
                    
                    {/* Formula Display */}
                    <div className="text-xs text-gray-500 mt-2 p-2 bg-gray-50 rounded">
                      <div>D(u,v,t) = d_com + d_proc</div>
                      <div>d_com = {metrics?.dataSize} × {metrics?.unitTransmissionDelay}</div>
                      <div>d_proc = {metrics?.isWarmStart ? '0' : 'cold_delay'} + {metrics?.dataSize} × {metrics?.unitProcessingTime}</div>
                    </div>
                  </div>
                );
              })()}
            </CardContent>
          </Card>

        {/* Algorithm Info */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Current Algorithm</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              <div className="font-medium mb-2">{models[selectedModel]}</div>
              <div className="text-xs text-gray-600">
                {selectedModel === "lstm" && "Long Short-Term Memory (LSTM) network is a type of recurrent neural network (RNN) that is well-suited for sequence prediction problems. It can learn long-term dependencies and is effective for time series forecasting."}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
