import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Target, AlertCircle } from "lucide-react";
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
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSelectChange = async (value) => {
    const previousAlgorithm = assignmentAlgorithm;
    setAssignmentAlgorithm(value);
    setError(null);
    setIsLoading(true);
    
    const result = await setServerAssignmentAlgorithm(value);
    setIsLoading(false);
    
    if (!result?.success) {
      setError(result?.error || "Failed to set algorithm");
      // Revert to previous algorithm on failure
      setAssignmentAlgorithm(previousAlgorithm);
    }
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
            disabled={isLoading}
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
          {error && (
            <div className="flex items-center gap-1 text-xs text-red-500">
              <AlertCircle className="w-3 h-3" />
              {error}
            </div>
          )}
          {assignmentAlgorithm === "predictive" && (
            <div className="text-xs text-amber-600">
              Note: Predictive requires 20+ history points per user
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
