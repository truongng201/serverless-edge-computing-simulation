import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function ModelSelectionCard({}) {
  const {
    selectedModel,
    setSelectedModel,
    models,
    predictionSteps,
    setPredictionSteps,
  } = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Model</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Prediction Model</Label>
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(models).map(([key, name]) => (
                <SelectItem key={key} value={key}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label className="text-xs">
            Prediction Steps: {predictionSteps[0]}
          </Label>
          <Slider
            value={predictionSteps}
            onValueChange={setPredictionSteps}
            max={20}
            min={5}
            step={1}
          />
        </div>
      </CardContent>
    </Card>
  );
}
