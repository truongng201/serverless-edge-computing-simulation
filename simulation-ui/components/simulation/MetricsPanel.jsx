import React from "react";
import useSimulationStore from "@/hooks/use-simulation-store";

// MetricsPanel: Right side panel with system metrics, node/user status, algorithm info
export default function MetricsPanel(props) {
  const { rightPanelOpen } = useSimulationStore();
  return (
    <div
      className={`absolute right-0 top-0 h-full bg-white shadow-lg transition-transform duration-300 ${
        rightPanelOpen ? "translate-x-0" : "translate-x-80"
      } w-80 z-10`}
    >
      <div className="p-4 h-full overflow-y-auto">{props.children}</div>
    </div>
  );
}
