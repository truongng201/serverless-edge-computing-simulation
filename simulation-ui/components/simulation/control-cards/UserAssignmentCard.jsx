// ...existing code...
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Target } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import React, { useState, useEffect } from "react";
import {
  setServerAssignmentAlgorithm,
  getAllAssignmentAlgorithms,
  getCurrentAssignmentAlgorithm,
} from "@/lib/user-management";

export default function UserAssignmentCard({}) {
  const { assignmentAlgorithm, setAssignmentAlgorithm } = useGlobalState();

  const [algorithms, setAlgorithms] = useState([]);

  const handleSelectChange = async (value) => {
    setAssignmentAlgorithm(value);
    await setServerAssignmentAlgorithm(value);
  };

  useEffect(() => {
    const fetchData = async () => {
      // Fetch all algorithms first so we know valid choices
      const allAlgorithms = await getAllAssignmentAlgorithms();
      setAlgorithms(allAlgorithms || []);

      // Then get current algorithm; if none, default to the first available
      let currentAlgorithm = await getCurrentAssignmentAlgorithm();
      
      if (currentAlgorithm) {
        setAssignmentAlgorithm(currentAlgorithm);
      }
    };
    fetchData();
  }, [setAssignmentAlgorithm]);

  console.log("Current assignment algorithm:", assignmentAlgorithm);
  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="w-4 h-4" />
          User Assignment
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label className="text-xs">Assignment Algorithm</Label>
          <Select
            value={assignmentAlgorithm ?? ""}
            onValueChange={handleSelectChange}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            {algorithms.length > 0 && (
              <SelectContent>
                {algorithms.map((algo) => (
                  <SelectItem key={algo} value={algo}>
                    {algo}
                  </SelectItem>
                ))}
              </SelectContent>
            )}
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
// ...existing code...
