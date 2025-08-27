import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Database } from "lucide-react";

export default function CentralNodeSettingsCard() {
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Database className="w-4 h-4" />
          Central Nodes
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-xs text-blue-600 p-2 bg-blue-50 rounded">
          Central Node managed by live backend system
        </div>
      </CardContent>
    </Card>
  );
}
