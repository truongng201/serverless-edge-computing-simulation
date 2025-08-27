"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { MapPin, Settings } from "lucide-react";
import ControlPanel from "@/components/simulation/ControlPanel";
import MetricsPanel from "@/components/simulation/MetricsPanel";
import SimulationCanvas from "@/components/simulation/SimulationCanvas";
import EditModeDescription from "@/components/simulation/EditModeDescription";
import ControlPanelContent from "@/components/simulation/ControlPanelContent";
import MetricsPanelContent from "@/components/simulation/MetricsPanelContent";

// Import custom hooks and utilities
import useGlobalState from "@/hooks/use-global-state";
import {
  useSimulationLogic,
  getEditModeDescription,
} from "@/lib/simulation-logic";
import { useCanvasDrawing } from "@/lib/canvas-drawing";

export default function Component() {
  // Get all state from the custom hook
  const { leftPanelOpen, setLeftPanelOpen, rightPanelOpen, setRightPanelOpen } =
    useGlobalState();

  // Get simulation logic
  const { simulationStep } = useSimulationLogic();

  // Get canvas drawing
  const { draw } = useCanvasDrawing();

  // Animation loop
  useEffect(() => {
    const interval = setInterval(() => {
      simulationStep();
      draw();
    }, 100);

    return () => clearInterval(interval);
  }, [simulationStep, draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-gray-50">
      {/* Full Screen Canvas */}
      <SimulationCanvas />

      {/* Left Control Panel */}
      <ControlPanel>
        <ControlPanelContent />
      </ControlPanel>

      {/* Right Metrics Panel */}
      <MetricsPanel>
        <MetricsPanelContent />
      </MetricsPanel>

      {/* Toggle Buttons for Panels */}
      {!leftPanelOpen && (
        <Button
          className="absolute left-4 top-4 z-20"
          size="sm"
          onClick={() => setLeftPanelOpen(true)}
        >
          <Settings className="w-4 h-4" />
        </Button>
      )}
      {!rightPanelOpen && (
        <Button
          className="absolute right-4 top-4 z-20"
          size="sm"
          onClick={() => setRightPanelOpen(true)}
        >
          <MapPin className="w-4 h-4" />
        </Button>
      )}

      {/* Instructions */}
      <EditModeDescription description={getEditModeDescription()} />
    </div>
  );
}
