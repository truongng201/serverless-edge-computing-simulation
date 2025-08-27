import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Plus, Minus, RotateCcw } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";

export default function ZoomControlsCard() {
  const { zoomLevel, setZoomLevel } = useGlobalState();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Zoom & Pan</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button
            onClick={() => setZoomLevel((prev) => Math.min(prev * 1.2, 5))}
            size="sm"
            variant="outline"
            className="flex-1"
          >
            <Plus className="w-4 h-4" />
            Zoom In
          </Button>
          <Button
            onClick={() => setZoomLevel((prev) => Math.max(prev / 1.2, 0.2))}
            size="sm"
            variant="outline"
            className="flex-1"
          >
            <Minus className="w-4 h-4" />
            Zoom Out
          </Button>
        </div>
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
