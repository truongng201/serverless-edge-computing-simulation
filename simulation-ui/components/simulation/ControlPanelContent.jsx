import {
  EdgeNodeSettingsCard,
  CentralNodeSettingsCard,
  UserSettingsCard,
  EditModeCard,
  ClearControlsCard,
  SimulationControlsCard,
  NodePlacementCard,
  UserAssignmentCard,
  LiveSystemStatusCard,
  ScenarioSelectionCard,
  ZoomControlsCard,
  ModelSelectionCard,
} from "./control-cards/ControlCards";
import { ChevronLeft } from "lucide-react";
import { useEffect, useRef } from "react";
import useGlobalState from "@/hooks/use-global-state";
import { calculateLatency } from "@/lib/helper";
import { runGAPAssignment } from "@/lib/user-management";
import { getClusterStatusAndUsersData } from "@/lib/simulation-management";

export default function ControlPanelContent() {
  const intervalRef = useRef(null);
  const {
    users,
    setUsers,
    leftPanelOpen,
    setLeftPanelOpen,
    simulationSpeed,
    edgeNodes,
    centralNodes,
  } = useGlobalState();

  // Function to run GAP batch assignment
  const runGAPBatch = () => {
    if (typeof runGAPAssignment === "function") {
      runGAPAssignment(users, edgeNodes, centralNodes, setUsers, {
        method: "greedy",
        enableMemoryConstraints: false,
        debug: true,
      });
    }
  };

  // Start live data polling
  const startLiveDataPolling = async () => {
    await getClusterStatusAndUsersData();

    // Start real-time polling with interval based on simulation speed
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    const intervalMs = Math.max(1000, 5000 / simulationSpeed[0]);
    intervalRef.current = setInterval(getClusterStatusAndUsersData, intervalMs);
  };

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Periodic auto (re)assignment every 10s: pick min latency among all edges and centrals
  useEffect(() => {
    const interval = setInterval(() => {
      if ((edgeNodes?.length || 0) + (centralNodes?.length || 0) === 0) return;
      if (!users || users.length === 0) return;

      setUsers((prev) =>
        prev.map((u) => {
          let bestLatency = Number.POSITIVE_INFINITY;
          let bestType = null;
          let bestId = null;

          // Evaluate all edges
          for (let i = 0; i < edgeNodes.length; i++) {
            const n = edgeNodes[i];
            const lat = calculateLatency(
              u,
              n.id,
              "edge",
              edgeNodes,
              centralNodes,
              window.__LATENCY_PARAMS__
            );
            if (lat < bestLatency) {
              bestLatency = lat;
              bestType = "edge";
              bestId = n.id;
            }
          }

          // Evaluate all centrals
          for (let i = 0; i < centralNodes.length; i++) {
            const c = centralNodes[i];
            const lat = calculateLatency(
              u,
              c.id,
              "central",
              edgeNodes,
              centralNodes,
              window.__LATENCY_PARAMS__
            );
            if (lat < bestLatency) {
              bestLatency = lat;
              bestType = "central";
              bestId = c.id;
            }
          }

          if (!bestType || !bestId || !isFinite(bestLatency)) return u;

          return {
            ...u,
            assignedEdge: bestType === "edge" ? bestId : null,
            assignedCentral: bestType === "central" ? bestId : null,
            latency: bestLatency,
          };
        })
      );
    }, 10000);

    return () => clearInterval(interval);
  }, [edgeNodes, centralNodes, users]);

  return (
    <>
      {/* Close panel - small left arrow button at the very top, outside all cards */}
      <div className="relative w-full">
        <button
          onClick={() => setLeftPanelOpen && setLeftPanelOpen(!leftPanelOpen)}
          className="absolute right-2 z-30 p-1 rounded hover:bg-gray-200 focus:outline-none"
          aria-label="Close panel"
          type="button"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      </div>
      <div className="pt-8">
        <EditModeCard />

        <LiveSystemStatusCard startLiveDataPolling={startLiveDataPolling} />

        <SimulationControlsCard />

        <ClearControlsCard />

        <ScenarioSelectionCard />

        <NodePlacementCard />

        <UserAssignmentCard runGAPBatch={runGAPBatch} />

        <ZoomControlsCard />

        <ModelSelectionCard />

        <UserSettingsCard />

        <CentralNodeSettingsCard />

        <EdgeNodeSettingsCard />
      </div>
    </>
  );
}
