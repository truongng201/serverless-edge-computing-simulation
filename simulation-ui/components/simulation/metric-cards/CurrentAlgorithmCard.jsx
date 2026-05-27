import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Settings } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useEffect } from "react";
import { getCurrentAssignmentAlgorithm } from "@/lib/user-management/assignment-algorithm";

export default function CurrentAlgorithmCard() {
  const { assignmentAlgorithm } = useGlobalState();

  useEffect(() => {
    // Load current algorithm
    getCurrentAssignmentAlgorithm();
  }, []);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Assignment Algorithm
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Current:</span>
            <Badge variant={assignmentAlgorithm === "convex optimization" ? "default" : "secondary"}>
              {assignmentAlgorithm}
            </Badge>
          </div>
          
          <div className="text-xs text-gray-600">
            {assignmentAlgorithm === "greedy" &&
              "Rule-based greedy algorithm that assigns users to the nearest healthy edge node within coverage and resource constraints. Fast but may not be globally optimal."}
            {assignmentAlgorithm === "greedy + keep-alive" &&
              "Nearest-node assignment with normal warm-container retention. This baseline isolates generic keep-alive reuse without mobility foresight."}
            {assignmentAlgorithm === "sticky greedy" &&
              "Keeps a user on the previously assigned node if it remains feasible; otherwise falls back to nearest-node assignment. This tests whether gains come mainly from avoiding switches."}
            {assignmentAlgorithm === "convex optimization" &&
              "CVX-based convex optimization that minimizes total cost (turnaround time + migration cost + cold start penalty) subject to coverage and resource constraints. Mathematically optimal but computationally intensive."}
            {assignmentAlgorithm === "predictive" &&
              "Mobility-predictive assignment using the T-Drive predictor output to choose a likely future-serving node."}
            {assignmentAlgorithm === "prediction without warm-state-awareness" &&
              "Uses mobility prediction for placement, but simulated execution does not preserve warm-state benefit. This isolates the contribution of prediction alone."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
