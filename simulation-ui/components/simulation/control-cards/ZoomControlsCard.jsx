import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Plus, Minus, RotateCcw } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function ZoomControlsCard({
  zoomIn,
  zoomOut,
  resetZoom,
}) {
  const {zoomLevel} = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Zoom & Pan</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button
            onClick={zoomIn}
            size="sm"
            variant="outline"
            className="flex-1"
          >
            <Plus className="w-4 h-4" />
            Zoom In
          </Button>
          <Button
            onClick={zoomOut}
            size="sm"
            variant="outline"
            className="flex-1"
          >
            <Minus className="w-4 h-4" />
            Zoom Out
          </Button>
        </div>
        <Button
          onClick={resetZoom}
          size="sm"
          variant="outline"
          className="w-full"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Reset View
        </Button>
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span>Zoom Level</span>
            <span>{(zoomLevel * 100).toFixed(0)}%</span>
          </div>
          <Progress
            value={((zoomLevel - 0.2) / (5 - 0.2)) * 100}
            className="h-2"
          />
        </div>
      </CardContent>
    </Card>
  );
}
