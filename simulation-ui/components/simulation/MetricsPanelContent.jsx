import { ChevronRight } from "lucide-react";
import {
  SystemStatusCard,
  StreetMapMetricsCard,
  LiveSystemMetricsCard,
  ConnectionStatusCard,
  CurrentAlgorithmCard,
} from "./metric-cards/MetricCards";
import useGlobalState from "@/hooks/use-global-state";

export default function MetricsPanelContent() {
  const { rightPanelOpen, setRightPanelOpen } = useGlobalState();
  return (
    <>
      {/* Close panel - small right arrow button at the very top, outside all cards */}
      <div className="relative w-full">
        <button
          onClick={() =>
            setRightPanelOpen && setRightPanelOpen(!rightPanelOpen)
          }
          className="absolute left-2 z-30 p-1 rounded hover:bg-gray-200 focus:outline-none"
          aria-label="Close panel"
          type="button"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      <div className="pt-8">
        <SystemStatusCard />

        <StreetMapMetricsCard />

        <LiveSystemMetricsCard />

        <ConnectionStatusCard />

        <CurrentAlgorithmCard />
      </div>
    </>
  );
}
