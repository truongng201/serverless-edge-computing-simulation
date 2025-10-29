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
import { startDactSample, startRandomGeneratedSample, getDatasetInfo } from "@/lib/simulation-management";
import { clearAllUsers } from "@/lib/user-management";
import { useEffect, useState } from "react";

export default function DatasetSelectionCard() {
  const { selectedDataset, setSelectedDataset, datasetInfo, setDatasetInfo } = useGlobalState();
  const [sampleSize, setSampleSize] = useState(100);

  const handleDatasetChange = async (value) => {
    setSelectedDataset(value);

    if (value === "Dataset2") {
      await startDactSample();
    } else if (value === "Dataset3") {
      await startRandomGeneratedSample();
    } else if (value === "none") {
      await clearAllUsers();
    }
  };

  useEffect(() => {
    const fetchDatasetInfo = async () => {
      const response = await getDatasetInfo();
      setDatasetInfo(response);
    };
    fetchDatasetInfo();
  }, []);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Navigation className="w-4 h-4" />
          Dataset Selection
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Dataset</Label>
          <Select value={selectedDataset} onValueChange={handleDatasetChange}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Select a dataset" />
            </SelectTrigger>
            <SelectContent>
              {datasetInfo?.dataset_list?.length > 0 ? (
                datasetInfo.dataset_list.map((dataset) => (
                  <SelectItem key={dataset.name} value={dataset.name}>
                    {dataset.ui_name}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="none">No datasets available</SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>

        {selectedDataset === "random_generated" && (
          <div className="space-y-2">
            <Label className="text-xs">Sample Size</Label>
            <Select value={sampleSize.toString()} onValueChange={(value) => setSampleSize(Number(value))}>
              <SelectTrigger className="h-8">
                <SelectValue placeholder="Select a sample size" />
              </SelectTrigger>
              <SelectContent>
                {[100, 200, 300, 400, 500, 600, 700, 800, 900, 1000].map((size) => (
                  <SelectItem key={size} value={size.toString()}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="text-xs text-gray-600">
          Select a predefined Dataset to load sample data, or choose "None" to
          manually add users.
        </div>
      </CardContent>
    </Card>
  );
}
