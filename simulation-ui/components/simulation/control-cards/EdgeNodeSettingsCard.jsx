import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import useGlobalState from "@/hooks/use-global-state";
import { updateEdgeCoverage } from "@/lib/node-management";

export default function EdgeNodeSettingsCard() {
  const { edgeCoverage } = useGlobalState();

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Edge Nodes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
          Edge Nodes managed by live backend system
        </div>

        <div className="space-y-2">
          <Label className="text-xs">Coverage: {edgeCoverage[0]}px</Label>
          <Slider
            value={edgeCoverage}
            onValueChange={updateEdgeCoverage}
            max={1000}
            min={0}
            step={10}
          />
        </div>
      </CardContent>
    </Card>
  );
}
