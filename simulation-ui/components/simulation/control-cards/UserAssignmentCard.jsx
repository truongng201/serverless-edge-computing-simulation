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
import { Target, MapPin, Settings2 } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { runAssignmentAlgorithm } from "@/lib/user-management";
import { useEffect, useState } from "react";

export default function UserAssignmentCard({
  runGAPBatch,
}) {
  const {
    edgeNodes,
    assignmentAlgorithm,
    setAssignmentAlgorithm,
    centralNodes,
    users,
  } = useGlobalState();

  // Local config states (load from backend on mount)
  const [dwell, setDwell] = useState(1.0);
  const [threshold, setThreshold] = useState(0.1);
  const [scanInterval, setScanInterval] = useState(0.5);
  const [serverStrategy, setServerStrategy] = useState(null);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        if (!process.env.NEXT_PUBLIC_API_URL) return;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/status`);
        if (!res.ok) return;
        const payload = await res.json();
        const strat = payload?.data?.strategy;
        if (strat) setServerStrategy(strat);
        const cfg = payload?.data?.config || {};
        if (typeof cfg.handoff_min_dwell_seconds === "number") setDwell(cfg.handoff_min_dwell_seconds);
        if (typeof cfg.handoff_improvement_threshold === "number") setThreshold(cfg.handoff_improvement_threshold);
        if (typeof cfg.assignment_scan_interval === "number") setScanInterval(cfg.assignment_scan_interval);
      } catch (e) {
        // ignore
      }
    };
    loadStatus();
    // Light auto refresh every 5s (strategy only)
    const id = setInterval(async () => {
      try {
        if (!process.env.NEXT_PUBLIC_API_URL) return;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/status`);
        if (!res.ok) return;
        const payload = await res.json();
        const strat = payload?.data?.strategy;
        if (strat) setServerStrategy(strat);
      } catch {}
    }, 5000);
    return () => clearInterval(id);
  }, []);
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
        // Refresh status to update badge
        try {
          const st = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/status`);
          const payload = await st.json();
          setServerStrategy(payload?.data?.strategy || strategy);
        } catch {}
      }
    } catch (e) {
      console.warn("Failed to set backend assignment strategy", e);
    }
  };

  const applyConfig = async () => {
    try {
      if (!process.env.NEXT_PUBLIC_API_URL) return;
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/config`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            handoff_min_dwell_seconds: Number(dwell),
            handoff_improvement_threshold: Number(threshold),
            assignment_scan_interval: Number(scanInterval),
          }),
        }
      );
      // Optionally refresh status
      try {
        const st = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment/status`);
        const payload = await st.json();
        setServerStrategy(payload?.data?.strategy || serverStrategy);
      } catch {}
    } catch (e) {
      console.warn("Failed to update assignment config", e);
    }
  };

  const strategyLabel = (s) => {
    switch (s) {
      case "geographic":
        return "Nearest Distance";
      case "least_loaded":
        return "Nearest Latency";
      case "gap_baseline":
        return "GAP Baseline";
      case "predictive":
        return "Predictive (GNN)";
      case "round_robin":
        return "Round Robin";
      default:
        return s || "Unknown";
    }
  };

  const strategyBadgeClass = (s) => {
    const base = "text-[10px] px-2 py-0.5 rounded-full border";
    switch (s) {
      case "geographic":
        return `${base} bg-blue-50 text-blue-700 border-blue-200`;
      case "least_loaded":
        return `${base} bg-amber-50 text-amber-700 border-amber-200`;
      case "gap_baseline":
        return `${base} bg-purple-50 text-purple-700 border-purple-200`;
      case "predictive":
        return `${base} bg-emerald-50 text-emerald-700 border-emerald-200`;
      default:
        return `${base} bg-gray-100 text-gray-700 border-gray-200`;
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="w-4 h-4" />
          User Assignment
          {serverStrategy && (
            <span className={strategyBadgeClass(serverStrategy)}>
              Strategy: {strategyLabel(serverStrategy)}
            </span>
          )}
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

        {/* Online assignment tuning */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium">
            <Settings2 className="w-3 h-3" /> Online Reassignment
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Dwell: {dwell.toFixed(2)} s</Label>
            <Slider
              value={[dwell]}
              onValueChange={(v) => setDwell(v[0])}
              min={0}
              max={3}
              step={0.1}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Threshold: {(threshold * 100).toFixed(0)}%</Label>
            <Slider
              value={[threshold]}
              onValueChange={(v) => setThreshold(v[0])}
              min={0}
              max={0.5}
              step={0.01}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Scan interval: {scanInterval.toFixed(2)} s</Label>
            <Slider
              value={[scanInterval]}
              onValueChange={(v) => setScanInterval(v[0])}
              min={0.1}
              max={2}
              step={0.1}
            />
          </div>
          <Button size="sm" variant="outline" onClick={applyConfig}>
            Apply Assignment Config
          </Button>
        </div>

        <div className="text-xs text-gray-600 mb-2">
          <div>Edge Servers: {edgeNodes.length}</div>
          <div>Central Servers: {centralNodes.length}</div>
          <div>Users: {users?.length || 0}</div>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <Button
            onClick={runAssignmentAlgorithm}
            size="sm"
            variant="outline"
            className="w-full"
            disabled={
              !users?.length || (!edgeNodes.length && !centralNodes.length)
            }
          >
            <MapPin className="w-4 h-4 mr-1" />
            Run User Assignment
          </Button>

          {assignmentAlgorithm === "gap-baseline" && (
            <Button
              onClick={() => runGAPBatch()}
              size="sm"
              variant="default"
              className="w-full bg-blue-600 hover:bg-blue-700"
              disabled={
                !users?.length || (!edgeNodes.length && !centralNodes.length)
              }
            >
              <Target className="w-4 h-4 mr-1" />
              Run GAP Batch (Optimal)
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
