import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Navigation } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { startDactSample, startVehiclesSample, initializeStreetMap } from "@/lib/simulation-management";
import { clearAllUsers } from "@/lib/user-management";

export default function ScenarioSelectionCard() {
  const { setRoadNetwork, selectedScenario, setSelectedScenario } = useGlobalState();

  const handleScenarioChange = async (value) => {
    setSelectedScenario(value);

    if (value === "scenario2") {
      await startDactSample();
    } else if (value === "scenario3") {
      await startVehiclesSample();
    } else if (value === "scenario4") {
      await initializeStreetMap();
    } else if (value === "none") {
      await clearAllUsers();
      setRoadNetwork(null);
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Navigation className="w-4 h-4" />
          Scenario Selection
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Scenario</Label>
          <Select value={selectedScenario} onValueChange={handleScenarioChange}>
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None (Self adding user)</SelectItem>
              <SelectItem value="scenario2">Scenario 2: DACT Sample</SelectItem>
              <SelectItem value="scenario3">
                Scenario 3: Vehicle Sample
              </SelectItem>
              <SelectItem value="scenario4">
                Scenario 4: Street Map
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="text-xs text-gray-600">
          Select a predefined scenario to load sample data, or choose "None" to
          manually add users.
        </div>
      </CardContent>
    </Card>
  );
}
