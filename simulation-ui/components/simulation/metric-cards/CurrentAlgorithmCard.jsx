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
            <Badge variant="secondary">
              {assignmentAlgorithm}
            </Badge>
          </div>
          
          <div className="text-xs text-gray-600">
            {assignmentAlgorithm === "greedy" &&
              "Tier-aware greedy baseline that prefers healthy feasible edges first, then warning, then unhealthy, and chooses the nearest node within the best available tier."}
            {assignmentAlgorithm === "random" &&
              "Random baseline that assigns each user to a feasible node uniformly at random. It provides a weak lower baseline for comparison."}
            {assignmentAlgorithm === "round robin" &&
              "Round-robin baseline that cycles users across feasible edge nodes to balance load, without using mobility or distance information."}
            {assignmentAlgorithm === "nearest" &&
              "Pure nearest-node baseline that selects the geographically closest feasible node without predictive or warm-state logic."}
            {assignmentAlgorithm === "greedy + keep-alive" &&
              "Nearest-node assignment with normal warm-container retention. This baseline isolates generic keep-alive reuse without mobility foresight."}
            {assignmentAlgorithm === "predictive" &&
              "Mobility-predictive assignment that ranks cloudlets using the T-Drive future-location forecast and selects the highest-probability feasible node."}
            {assignmentAlgorithm === "prediction without warm-state awareness" &&
              "Uses mobility prediction for placement, but simulated execution does not preserve warm-state benefit. This isolates the contribution of prediction alone."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
