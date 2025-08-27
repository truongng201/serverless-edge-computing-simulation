import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Target, MapPin } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function UserAssignmentCard({
  assignmentAlgorithm,
  setAssignmentAlgorithm,
  runAssignmentAlgorithm,
  runGAPBatch,
  users,
  centralNodes,
}) {
  const {edgeNodes} = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="w-4 h-4" />
          User Assignment
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Assignment Algorithm</Label>
          <Select
            value={assignmentAlgorithm}
            onValueChange={setAssignmentAlgorithm}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="nearest-distance">
                Nearest Distance
              </SelectItem>
              <SelectItem value="nearest-latency">
                Nearest Latency
              </SelectItem>
              <SelectItem value="gap-baseline">GAP Baseline</SelectItem>
              <SelectItem value="random">Random Assignment</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="text-xs text-gray-600 mb-2">
          <div>Edge Servers: {edgeNodes.length}</div>
          <div>Central Servers: {centralNodes.length}</div>
          <div>Users: {users?.length || 0}</div>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <Button
            onClick={runAssignmentAlgorithm}
            size="sm"
            variant="outline"
            className="w-full"
            disabled={
              !users?.length || (!edgeNodes.length && !centralNodes.length)
            }
          >
            <MapPin className="w-4 h-4 mr-1" />
            Run User Assignment
          </Button>

          {assignmentAlgorithm === "gap-baseline" && (
            <Button
              onClick={() => runGAPBatch()}
              size="sm"
              variant="default"
              className="w-full bg-blue-600 hover:bg-blue-700"
              disabled={
                !users?.length ||
                (!edgeNodes.length && !centralNodes.length)
              }
            >
              <Target className="w-4 h-4 mr-1" />
              Run GAP Batch (Optimal)
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
