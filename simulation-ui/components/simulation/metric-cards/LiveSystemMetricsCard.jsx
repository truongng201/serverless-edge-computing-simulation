import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Database, Server } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function LiveSystemMetricsCard() {
  const { liveData } = useSimulationStore();

  if (!liveData) {
    return null;
  }

  return (
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
              <span>CPU ({liveData.central_node?.system_info?.cpu_cores_physical} cores):</span>
              <span className="font-medium">{liveData.central_node?.cpu_usage?.toFixed(1)}%</span>
            </div>
            <Progress value={liveData.central_node?.cpu_usage || 0} className="h-2" />
            
            <div className="flex justify-between">
              <span>Memory ({liveData.central_node?.system_info?.memory_total} GB):</span>
              <span className="font-medium">{liveData.central_node?.memory_usage?.toFixed(1)}%</span>
            </div>
            <Progress value={liveData.central_node?.memory_usage || 0} className="h-2" />
            
            <div className="flex justify-between">
              <span>Active Requests:</span>
              <Badge variant="outline" className="text-xs">
                {liveData.central_node?.active_requests || 0}
              </Badge>
            </div>

            <div className="flex justify-between">
              <span>Total Requests:</span>
              <Badge variant="outline" className="text-xs">
                {liveData.central_node?.total_requests || 0}
              </Badge>
            </div>
            
            <div className="flex justify-between">
              <span>Warm containers:</span>
              <Badge variant="outline" className="text-xs">
                {liveData.central_node?.warm_container || 0}
              </Badge>
            </div>

            <div className="flex justify-between">
              <span>Running containers:</span>
              <Badge variant="outline" className="text-xs">
                {liveData.central_node?.running_container || 0}
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
              <div className="font-medium text-lg">{liveData.cluster_info?.total_nodes || 0}</div>
              <div className="text-gray-600">Total</div>
            </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <div className="font-medium text-lg text-green-600">{liveData.cluster_info?.healthy_node_count || 0}</div>
              <div className="text-gray-600">Healthy</div>
            </div>

            <div className="text-center">
              <div className="font-medium text-lg text-yellow-600">{liveData.cluster_info?.warning_node_count || 0}</div>
              <div className="text-gray-600">Warning</div>
            </div>
            <div className="text-center">
              <div className="font-medium text-lg text-red-600">{liveData.cluster_info?.unhealthy_node_count || 0}</div>
              <div className="text-gray-600">Unhealthy</div>
            </div>
          </div>
        </div>
        
        {/* Individual Edge Node Status */}
        <div className="space-y-2">
          <div className="font-medium text-sm text-gray-700">Individual Node Status</div>
          {liveData.cluster_info?.edge_nodes_info?.map((node, index) => (
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
  );
}
