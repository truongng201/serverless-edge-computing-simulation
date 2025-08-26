import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Edit3, Trash2 } from "lucide-react";
import useSimulationStore from "@/hooks/use-simulation-store";

export default function EditModeCard({
  deleteSelectedNode,
  deleteSelectedUser,
}) {
  const {
    editMode,
    setEditMode,
    selectedEdge,
    selectedCentral,
    selectedUser
  } = useSimulationStore();
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Edit3 className="w-4 h-4" />
          Edit Mode
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Edit Mode</Label>
          <Select value={editMode} onValueChange={setEditMode}>
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None - Add Users</SelectItem>
              <SelectItem value="drag">Drag - Pan View</SelectItem>
              <SelectItem value="nodes">Nodes Only</SelectItem>
              <SelectItem value="users">Users Only</SelectItem>
              <SelectItem value="both">Nodes & Users</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {editMode !== "none" && (
          <div className="text-xs text-gray-600 space-y-1">
            {editMode === "drag" ? (
              <>
                <div>• Drag to pan the view</div>
                <div>• Mouse wheel to zoom</div>
                <div>• Click to select elements</div>
              </>
            ) : (
              <>
                <div>• Drag to move elements</div>
                <div>• Click to select elements</div>
                <div>• Dashed rings show editable items</div>
              </>
            )}
          </div>
        )}
        {(selectedEdge || selectedCentral) && (
          <Button
            onClick={deleteSelectedNode}
            size="sm"
            variant="destructive"
            className="w-full"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Selected Node
          </Button>
        )}
        {selectedUser && (
          <Button
            onClick={deleteSelectedUser}
            size="sm"
            variant="destructive"
            className="w-full"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Selected User
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
