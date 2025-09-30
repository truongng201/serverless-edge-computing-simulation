import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Activity, Clock, Users, RefreshCw } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useState, useEffect } from "react";
import { 
  fetchPerformanceMetrics, 
  startPerformanceMetricsAutoRefresh,
  stopPerformanceMetricsAutoRefresh 
} from "@/lib/simulation-management/performance-metrics";

export default function PerformanceMetricsCard() {
  const { 
    performanceMetrics, 
    algorithmComparison,
    assignmentAlgorithm,
    cloudletMetrics 
  } = useGlobalState();
  
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(null);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh) {
      const intervalId = startPerformanceMetricsAutoRefresh(3000); // Refresh every 3 seconds
      setRefreshInterval(intervalId);
      return () => stopPerformanceMetricsAutoRefresh(intervalId);
    } else if (refreshInterval) {
      stopPerformanceMetricsAutoRefresh(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh]);

  useEffect(() => {
    fetchPerformanceMetrics();
  }, []);

  const handleRefresh = async () => {
    setIsLoading(true);
    await fetchPerformanceMetrics();
    setIsLoading(false);
  };



  const formatNumber = (num) => {
    if (num === 0) return "0";
    if (num < 1) return num.toFixed(3);
    if (num < 100) return num.toFixed(2);
    return Math.round(num).toLocaleString();
  };

  const formatMs = (ms) => {
    if (ms < 1000) return `${formatNumber(ms)}ms`;
    return `${formatNumber(ms / 1000)}s`;
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Performance Metrics
          </CardTitle>
          <div className="flex items-center gap-1">
            {/* <Button
              size="sm"
              variant="ghost"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="h-6 px-2"
            >
              <RefreshCw className={`w-3 h-3 ${autoRefresh ? 'animate-spin' : ''}`} />
            </Button> */}
            <Button
              size="sm"
              variant="ghost"
              onClick={handleRefresh}
              disabled={isLoading}
              className="h-6 px-2"
            >
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Current Algorithm */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Algorithm:</span>
            <Badge variant={assignmentAlgorithm === "convex optimization" ? "default" : "secondary"}>
              {assignmentAlgorithm}
            </Badge>
          </div>

          {/* Total Cost */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Total Cost:
            </span>
            <span className="font-mono text-xs">
              {formatMs(performanceMetrics.total_cost)}
            </span>
          </div>

          {/* Component Breakdown */}
          <div className="space-y-1 pl-2 border-l-2 border-gray-100">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Turnaround Time:</span>
              <span className="font-mono text-xs">
                {formatMs(performanceMetrics.total_turnaround_time)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Migration Cost:</span>
              <span className="font-mono text-xs">
                {formatMs(performanceMetrics.total_migration_cost)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Cold Start Penalty:</span>
              <span className="font-mono text-xs">
                {formatMs(performanceMetrics.total_cold_start_penalty)}
              </span>
            </div>
          </div>

        </div>
      </CardContent>
    </Card>
  );
}