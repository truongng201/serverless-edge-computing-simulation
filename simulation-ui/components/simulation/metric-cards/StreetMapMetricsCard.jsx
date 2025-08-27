import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Car } from "lucide-react";
import { getStreetMapStats } from "../../../lib/street-map-users";
import useGlobalState from "@/hooks/use-global-state";

export default function StreetMapMetricsCard() {
  const { selectedScenario, roadNetwork, users } = useGlobalState();
  if (selectedScenario !== "scenario4" || !roadNetwork) {
    return null;
  }

  const streetStats = getStreetMapStats(users, roadNetwork);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Car className="w-4 h-4 text-blue-600" />
          Street Map Simulation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-center bg-blue-50 p-2 rounded">
            <div className="font-medium text-lg text-blue-600">{streetStats.totalUsers}</div>
            <div className="text-gray-600">Total Vehicles</div>
          </div>
          <div className="text-center bg-green-50 p-2 rounded">
            <div className="font-medium text-lg text-green-600">{streetStats.movingUsers}</div>
            <div className="text-gray-600">Moving</div>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-center bg-yellow-50 p-2 rounded">
            <div className="font-medium text-lg text-yellow-600">{streetStats.waitingAtLights}</div>
            <div className="text-gray-600">At Traffic Lights</div>
          </div>
          <div className="text-center bg-purple-50 p-2 rounded">
            <div className="font-medium text-lg text-purple-600">{streetStats.assignedUsers}</div>
            <div className="text-gray-600">Assigned to Nodes</div>
          </div>
        </div>
        
        <div className="bg-gray-50 p-2 rounded text-xs">
          <div className="flex justify-between mb-1">
            <span>Executing Functions:</span>
            <Badge variant="outline">{streetStats.executingFunctions}</Badge>
          </div>
          <div className="flex justify-between mb-1">
            <span>Avg Latency:</span>
            <Badge variant="outline">{Math.round(streetStats.averageLatency)}ms</Badge>
          </div>
          <div className="flex justify-between">
            <span>Traffic Lights:</span>
            <Badge variant="outline">{streetStats.activeTrafficLights} active</Badge>
          </div>
        </div>
        
        {/* Function Types Distribution */}
        <div className="space-y-1">
          <div className="text-xs font-medium text-gray-700">Function Types:</div>
          <div className="space-y-1">
            {Object.entries(streetStats.functionTypes).slice(0, 4).map(([type, count]) => (
              <div key={type} className="flex justify-between items-center text-xs">
                <span className="capitalize text-gray-600">{type.replace('_', ' ')}</span>
                <Badge variant="secondary" className="text-xs">{count}</Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
