import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Database, Plus, Minus } from "lucide-react";

export default function CentralNodeSettingsCard({
  simulationMode,
  addCentralNode,
  removeCentralNode,
  centralCoverage,
  handleCentralCoverageChange,
}) {
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Database className="w-4 h-4" />
          Central Nodes
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {simulationMode !== "real" && (
          <>
            <div className="flex gap-2">
              <Button
                onClick={addCentralNode}
                size="sm"
                variant="outline"
                className="flex-1"
              >
                <Plus className="w-4 h-4" />
                Add
              </Button>
              <Button
                onClick={removeCentralNode}
                size="sm"
                variant="outline"
                className="flex-1"
              >
                <Minus className="w-4 h-4" />
                Remove
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">
                Coverage: {centralCoverage[0]}px
              </Label>
              <Slider
                value={centralCoverage}
                onValueChange={handleCentralCoverageChange}
                max={1000}
                min={0}
                step={20}
              />
            </div>
          </>
        )}
        {simulationMode === "real" && (
          <>
            <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
              Central Node managed by real system
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
