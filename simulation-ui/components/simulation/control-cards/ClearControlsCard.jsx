import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";

export default function ClearControlsCard({ clearAllUsers }) {
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
        </div>
      </CardContent>
    </Card>
  );
}
