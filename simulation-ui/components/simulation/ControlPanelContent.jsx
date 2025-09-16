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
// import { calculateLatency } from "@/lib/helper"; // unused here
// Frontend assignment removed; backend is authoritative
// import { runGAPAssignment } from "@/lib/user-management";
import { getClusterStatusAndUsersData } from "@/lib/simulation-management";

export default function ControlPanelContent() {
  const intervalRef = useRef(null);
  const {
    users,
    leftPanelOpen,
    setLeftPanelOpen,
    simulationSpeed,
    edgeNodes,
    centralNodes,
  } = useGlobalState();

  // GAP batch (client-side) is deprecated; backend handles assignment

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

  // Removed client-side auto-assignment loop; backend handoff is authoritative

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

        <UserAssignmentCard />

        <ZoomControlsCard />

        <ModelSelectionCard />

        <UserSettingsCard />

        <CentralNodeSettingsCard />

        <EdgeNodeSettingsCard />
      </div>
    </>
  );
}
