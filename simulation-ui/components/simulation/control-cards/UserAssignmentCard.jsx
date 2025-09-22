import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Target } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useEffect, useState } from "react";

export default function UserAssignmentCard({}) {
  const {
    assignmentAlgorithm,
    setAssignmentAlgorithm,
  } = useGlobalState();

  
  // Map UI selection -> backend strategy
  const mapToBackend = (ui) => {
    switch (ui) {
      case "nearest-distance":
        return "geographic"; // distance-based
      case "nearest-latency":
        return "least_loaded"; // load-aware proxy
      case "gap-baseline":
        return "gap_baseline"; // GAP solver baseline
      case "predictive-gnn":
        return "predictive"; // predictive (GNN/trajectory)
      default:
        return "geographic";
    }
  };

  const onSelectAlgo = async (value) => {
    try {
      setAssignmentAlgorithm(value);
      if (process.env.NEXT_PUBLIC_API_URL) {
        const strategy = mapToBackend(value);
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/strategy`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ strategy }),
          }
        );
      }
    } catch (e) {
      console.warn("Failed to set backend assignment strategy", e);
    }
  };


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
          <Select value={assignmentAlgorithm} onValueChange={onSelectAlgo}>
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="nearest-distance">Nearest Distance</SelectItem>
              <SelectItem value="nearest-latency">Nearest Latency</SelectItem>
              <SelectItem value="gap-baseline">GAP Baseline</SelectItem>
              <SelectItem value="predictive-gnn">Predictive (GNN)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
