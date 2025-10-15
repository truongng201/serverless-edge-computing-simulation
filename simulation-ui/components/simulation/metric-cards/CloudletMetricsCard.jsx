import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Server, Users, Clock, Zap } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";

export default function CloudletMetricsCard() {
  const { cloudletMetrics } = useGlobalState();

  const formatNumber = (num) => {
    if (num === 0) return "0";
    if (num < 1) return num.toFixed(2);
    if (num < 100) return num.toFixed(1);
    return Math.round(num).toLocaleString();
  };

  const formatMs = (ms) => {
    if (ms < 1000) return `${formatNumber(ms)}ms`;
    return `${formatNumber(ms / 1000)}s`;
  };

  const getUtilizationColor = (percentage) => {
    if (percentage >= 90) return "text-red-600";
    if (percentage >= 70) return "text-yellow-600";
    return "text-green-600";
  };

  const getUtilizationBadgeVariant = (percentage) => {
    if (percentage >= 90) return "destructive";
    if (percentage >= 70) return "secondary";
    return "default";
  };

  if (!cloudletMetrics || Object.keys(cloudletMetrics).length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Server className="w-4 h-4" />
            Cloudlet Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-xs text-gray-500">No cloudlet data available</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Server className="w-4 h-4" />
          Cloudlet Metrics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(cloudletMetrics).map(([cloudletId, metrics]) => (
            <div key={cloudletId} className="space-y-2 p-2 border rounded-md">
              {/* Cloudlet Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {cloudletId === "central_node" ? "Central" : "Edge"}
                  </Badge>
                  <span className="font-mono text-xs">{cloudletId}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  <span className="text-xs font-mono">{metrics.num_users}</span>
                </div>
              </div>

              {/* Resource Utilization */}
              {cloudletId !== "central_node" && (
                <div className="space-y-2">
                  {/* Memory Utilization */}
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Memory:</span>
                      <span className={`text-xs font-mono ${getUtilizationColor(metrics.memory_utilization_percent)}`}>
                        {formatNumber(metrics.memory_utilization_percent)}%
                      </span>
                    </div>
                    <Progress 
                      value={Math.min(100, metrics.memory_utilization_percent)} 
                      className="h-1"
                    />
                  </div>

                  {/* CPU Utilization */}
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">CPU:</span>
                      <span className={`text-xs font-mono ${getUtilizationColor(metrics.cpu_utilization_percent)}`}>
                        {formatNumber(metrics.cpu_utilization_percent)}%
                      </span>
                    </div>
                    <Progress 
                      value={Math.min(100, metrics.cpu_utilization_percent)} 
                      className="h-1"
                    />
                  </div>

                  {/* Bandwidth Utilization */}
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Bandwidth:</span>
                      <span className={`text-xs font-mono ${getUtilizationColor(metrics.bandwidth_utilization_percent)}`}>
                        {formatNumber(metrics.bandwidth_utilization_percent)}%
                      </span>
                    </div>
                    <Progress 
                      value={Math.min(100, metrics.bandwidth_utilization_percent)} 
                      className="h-1"
                    />
                  </div>
                </div>
              )}

              {/* Performance Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Avg Latency:
                  </span>
                  <span className="font-mono">
                    {formatMs(metrics.avg_turnaround_time)}
                  </span>
                </div>
                
                {metrics.cold_starts > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500 flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      Cold Starts:
                    </span>
                    <Badge variant="destructive" className="text-xs">
                      {metrics.cold_starts}
                    </Badge>
                  </div>
                )}
              </div>

              {/* Resource Demands */}
              <div className="grid grid-cols-3 gap-1 text-xs text-gray-500 pt-1 border-t">
                <div>
                  <span>Memory:</span>
                  <span className="font-mono ml-1">
                    {formatNumber(metrics.total_memory_demand)}MB
                  </span>
                </div>
                <div>
                  <span>CPU:</span>
                  <span className="font-mono ml-1">
                    {formatNumber(metrics.total_cpu_demand)}
                  </span>
                </div>
                <div>
                  <span>BW:</span>
                  <span className="font-mono ml-1">
                    {formatNumber(metrics.total_bandwidth_demand)}Mbps
                  </span>
                </div>
              </div>

              {/* Status Indicator */}
              {cloudletId !== "central_node" && (
                <div className="flex justify-end">
                  <Badge 
                    variant={getUtilizationBadgeVariant(
                      Math.max(
                        metrics.memory_utilization_percent,
                        metrics.cpu_utilization_percent,
                        metrics.bandwidth_utilization_percent
                      )
                    )}
                    className="text-xs"
                  >
                    {Math.max(
                      metrics.memory_utilization_percent,
                      metrics.cpu_utilization_percent,
                      metrics.bandwidth_utilization_percent
                    ) >= 90 ? "Overloaded" : 
                     Math.max(
                      metrics.memory_utilization_percent,
                      metrics.cpu_utilization_percent,
                      metrics.bandwidth_utilization_percent
                    ) >= 70 ? "High Load" : "Normal"}
                  </Badge>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}