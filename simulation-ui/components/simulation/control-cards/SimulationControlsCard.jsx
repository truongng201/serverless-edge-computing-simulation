import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Play, Pause, RotateCcw } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function SimulationControlsCard({
  handleToggleSimulation,
  handleResetSimulation,
  simulationSpeed,
  setSimulationSpeed,
  predictionEnabled,
  setPredictionEnabled,
  users,
  simulationLoading,
}) {
  const { isSimulating } = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Simulation</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button
            onClick={handleToggleSimulation}
            variant={isSimulating ? "destructive" : "default"}
            size="sm"
            className="flex-1"
            disabled={users?.length === 0 || simulationLoading}
          >
            {isSimulating ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {simulationLoading
              ? "Loading..."
              : isSimulating
              ? "Stop"
              : "Start"}
          </Button>
          <Button
            onClick={handleResetSimulation}
            variant="outline"
            size="sm"
            disabled={simulationLoading}
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
        </div>
        {isSimulating && (
          <div className="text-xs text-green-600 font-medium flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            API Simulation Active
          </div>
        )}
        <div className="space-y-2">
          <Label className="text-xs">Speed: {simulationSpeed[0]}x</Label>
          <Slider
            value={simulationSpeed}
            onValueChange={setSimulationSpeed}
            max={5}
            min={0.1}
            step={0.1}
          />
        </div>
        <div className="flex items-center justify-between">
          <Label className="text-xs">Prediction</Label>
          <Switch
            checked={predictionEnabled}
            onCheckedChange={setPredictionEnabled}
          />
        </div>
      </CardContent>
    </Card>
  );
}
