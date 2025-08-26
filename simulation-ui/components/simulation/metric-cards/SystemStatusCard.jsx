import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Users, Timer } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function SystemStatusCard({
  users,
}) {
  const { liveData, totalLatency } = useSimulationStore();
  return (
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
            Total Latency (ms)
          </span>
          <Badge variant="outline">{Math.round(totalLatency || 0)}</Badge>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2">
            <Timer className="w-4 h-4" />
            Average Load
          </span>
          <Badge variant={liveData?.cluster_info?.average_load > 90 ? "destructive" : liveData?.cluster_info?.average_load > 70 ? "secondary" : "default"}>
            {Math.round(liveData?.cluster_info?.average_load, 2) ? Math.round(liveData?.cluster_info?.average_load, 2) : 0}%
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
  );
}
