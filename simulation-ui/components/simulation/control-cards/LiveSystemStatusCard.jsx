import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Server, Database, Play } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useEffect } from "react";
import { getClusterStatusAndUsersData } from "@/lib/simulation-management";

export default function LiveSystemStatusCard({ startLiveDataPolling }) {
  const { liveData, loadingData, dataError, setDataError } = useGlobalState();

  useEffect(() => {
    if (dataError != "") {
      setTimeout(() => {
        setDataError("");
      }, 3000);
    }
  }, [dataError]);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Server className="w-4 h-4" />
          Live System Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <div
            className={`p-2 rounded text-xs ${
              loadingData
                ? "bg-gray-50"
                : dataError === ""
                ? "bg-green-50"
                : "bg-red-50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span>Status:</span>
              <Badge
                variant="default"
                className={`text-xs ${
                  loadingData
                    ? "bg-gray-600"
                    : dataError === ""
                    ? "bg-green-600"
                    : "bg-red-600"
                }`}
              >
                {loadingData
                  ? "Loading..."
                  : dataError === ""
                  ? "Connected"
                  : "Not connected"}
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Button
              onClick={getClusterStatusAndUsersData}
              size="sm"
              variant="outline"
              disabled={loadingData}
              className="text-xs"
            >
              <Database className="w-3 h-3 mr-1" />
              Refresh
            </Button>

            <Button
              onClick={startLiveDataPolling}
              size="sm"
              variant="default"
              className="text-xs bg-green-600 hover:bg-green-700"
            >
              <Play className="w-3 h-3 mr-1" />
              Auto Poll
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
