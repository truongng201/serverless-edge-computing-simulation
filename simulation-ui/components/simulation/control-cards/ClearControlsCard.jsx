import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, Server, Database, Trash2 } from "lucide-react";

export default function ClearControlsCard({
  clearAllUsers,
  clearAllEdgeNodes,
  clearAllCentralNodes,
  clearEverything,
}) {
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Clear Controls</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <Button onClick={clearAllUsers} size="sm" variant="outline">
            <Users className="w-4 h-4 mr-1" />
            Users
          </Button>
          <Button onClick={clearAllEdgeNodes} size="sm" variant="outline">
            <Server className="w-4 h-4 mr-1" />
            Edges
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Button
            onClick={clearAllCentralNodes}
            size="sm"
            variant="outline"
          >
            <Database className="w-4 h-4 mr-1" />
            Central
          </Button>
          <Button onClick={clearEverything} size="sm" variant="destructive">
            <Trash2 className="w-4 h-4 mr-1" />
            All
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
