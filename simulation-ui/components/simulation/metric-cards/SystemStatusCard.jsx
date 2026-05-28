import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Activity, Clock, Users, RefreshCw, Timer } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useState, useEffect } from "react";
import { fetchPerformanceMetrics } from "@/lib/simulation-management";
import { formatMs } from "@/lib/helper";
import TATChart from "./TATChart";

export default function SystemStatusCard() {
  const { performanceMetrics, assignmentAlgorithm, liveData, users } =
    useGlobalState();

  const [isLoading, setIsLoading] = useState(false);

  

  useEffect(() => {
    fetchPerformanceMetrics();
  }, []);

  const handleRefresh = async () => {
    setIsLoading(true);
    await fetchPerformanceMetrics();
    setIsLoading(false);
  };

  

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="w-4 h-4" />
            System status
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
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">Algorithm:</span>
            <Badge variant="outline">{assignmentAlgorithm}</Badge>
          </div>
          
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              Total Turnaround time (TAT)
            </span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs">
                {Math.round(performanceMetrics.total_turnaround_time, 3)}ms
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              Detail chart for TAT
            </span>
            <div className="flex items-center gap-2">
              <TATChart />
            </div>
          </div>


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
              Average CPU Load
            </span>
            <Badge
              variant={
                liveData?.cluster_info?.average_load > 90
                  ? "destructive"
                  : liveData?.cluster_info?.average_load > 70
                  ? "secondary"
                  : "default"
              }
            >
              {Math.round(liveData?.cluster_info?.average_load, 2)
                ? Math.round(liveData?.cluster_info?.average_load, 2)
                : 0}
              %
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
