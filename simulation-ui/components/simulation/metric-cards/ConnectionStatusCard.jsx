import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import useSimulationStore from "@/hooks/use-simulation-store";
import { Timer } from "lucide-react";

export default function ConnectionStatusCard() {
  const { selectedUser, setSelectedUser, users } = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Connection Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {users.map((user) => (
          <div key={user.id}>
            <div
              className={`p-2 rounded cursor-pointer transition-colors text-xs ${
                selectedUser && selectedUser.id === user.id
                  ? "bg-purple-100"
                  : "hover:bg-gray-50"
              }`}
              onClick={() =>
                setSelectedUser(
                  selectedUser && selectedUser.id === user.id ? null : user
                )
              }
            >
              <div className="flex justify-between items-center mb-1">
                <span className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full bg-blue-500`} />
                  {user.id}
                </span>
              </div>
              <div className="text-gray-600">
                <span>
                  →{" "}
                  {user.assignedEdge || user.assignedCentral || "Disconnected"}
                </span>
              </div>
              <div className="text-gray-600">
                <span>
                  Last executed:{" "}
                  {user.last_executed_period
                    ? user.last_executed_period.toFixed(2) + " (s)"
                    : "Never"}
                </span>
              </div>
            </div>

            {/* Latency Details - Show when user is selected */}
            {selectedUser && selectedUser.id === user.id && (
              <div className="mt-2 ml-2 p-3 bg-purple-50 rounded border border-purple-200 space-y-2">
                <div className="text-xs font-medium text-purple-700 flex items-center gap-1">
                  <Timer className="w-3 h-3" />
                  Latency Breakdown
                </div>

                <div className="space-y-2">
                  {/* Communication Delay */}
                  <div className="space-y-1">
                    <div className="flex justify-center text-xs font-bold">
                      <span>Propagation delay (d/θ) (P)</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span>Value:</span>
                      <span className="font-mono">
                        {user.latency.propagation_delay?.toFixed(6) || 0} ms
                      </span>
                    </div>
                    <div className="ml-2 text-xs text-gray-500">
                      θ (propagation speed) = Speed of light in fiber = 3 * 10^8
                      m/s
                    </div>
                    <div className="ml-2 text-xs text-gray-500">
                      d (distance) = {user.latency.distance?.toFixed(2) || 0} m
                    </div>
                    <div className="flex justify-center text-xs font-bold">
                      <span>Transmission delay (s/β) (T)</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span>Value:</span>
                      <span className="font-mono">
                        {user.latency.transmission_delay?.toFixed(6) || 0} ms
                      </span>
                    </div>
                    <div className="ml-2 text-xs text-gray-500">
                      s (data size) = {user.latency.data_size || 0} Bytes
                    </div>
                    <div className="ml-2 text-xs text-gray-500">
                      β (bandwidth) = {user.latency.bandwidth || 0} Bytes/ms
                    </div>
                  </div>

                  {/* Computation Delay */}
                  <div className="space-y-1">
                    <div className="flex justify-center text-xs font-bold">
                      <span>Computation delay (C):</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span>Value:</span>
                      <span className="font-mono">
                        {user.latency.computation_delay?.toFixed(6) || 0} ms
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span>Container status (Warm/Cold):</span>
                      <span className="font-mono">
                        {user.latency.container_status || "None"}
                      </span>
                    </div>
                  </div>

                  {/* Total Latency turn around time */}
                  <div className="border-t pt-2 border-purple-200">
                    <div className="flex justify-center text-xs font-bold">
                      <span>Total turn around time (TAT)</span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>Value: </span>
                      <span className="font-mono">
                        {user.latency.total_turnaround_time?.toFixed(6) || 0} ms
                      </span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>Value in seconds: </span>
                      <span className="font-mono">
                        {(user.latency.total_turnaround_time / 1000).toFixed(
                          6
                        ) || 0}{" "}
                        s
                      </span>
                    </div>
                  </div>

                  {/* Formula Display */}
                  <div className="text-xs text-gray-500 mt-2 p-2 bg-white rounded border border-purple-100">
                    <div>TAT = C + Communication</div>
                    <div>Communication = P + T</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
