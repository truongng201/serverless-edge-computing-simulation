import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Target, MapPin } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function NodePlacementCard({ runPlacementAlgorithm, users }) {
  const { edgeNodes, placementAlgorithm, setPlacementAlgorithm } =
    useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="w-4 h-4" />
          Node Placement
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Placement Algorithm</Label>
          <Select
            value={placementAlgorithm}
            onValueChange={setPlacementAlgorithm}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="topk-demand">Top-K Demand</SelectItem>
              <SelectItem value="kmeans">K-Means Clustering</SelectItem>
              <SelectItem value="random-random">Random-Random</SelectItem>
              <SelectItem value="random-nearest">Random-Nearest</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={runPlacementAlgorithm}
          size="sm"
          variant="default"
          className="w-full"
          disabled={!users?.length || !edgeNodes.length}
        >
          <MapPin className="w-4 h-4 mr-1" />
          Run Node Placement
        </Button>
      </CardContent>
    </Card>
  );
}
