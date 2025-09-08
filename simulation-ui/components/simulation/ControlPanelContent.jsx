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
import { runAssignmentAlgorithm } from "@/lib/user-management/run-assignment-algorithm";
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
    isSimulating,
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

  // Automatic assignment algorithm every 2s when simulation is running
  useEffect(() => {
    const interval = setInterval(() => {
      // Only run auto-assignment when simulation is running
      if (!isSimulating) return;
      if ((edgeNodes?.length || 0) + (centralNodes?.length || 0) === 0) return;
      if (!users || users.length === 0) return;

      // Run assignment algorithm to automatically assign users to best nodes
      runAssignmentAlgorithm();
    }, 2000); // Run every 2 seconds

    return () => clearInterval(interval);
  }, [edgeNodes, centralNodes, users, isSimulating]);

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
