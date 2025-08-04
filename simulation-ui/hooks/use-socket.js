import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

export const useSocket = (
  serverUrl = "http://localhost:5001",
  isSimulating
) => {
  const socketRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [simulationData, setSimulationData] = useState(null);
  const [simulationStatus, setSimulationStatus] = useState("stopped");
  const [currentStep, setCurrentStep] = useState(659);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (isSimulating) {
      socketRef.current = io(serverUrl, {
        transports: ["websocket", "polling"],
      });
      const socket = socketRef.current;
      socket.on("connect", () => {
        console.log("Connected to server");
        setIsConnected(true);
      });

      socket.on("disconnect", () => {
        console.log("Disconnected from server");
        setIsConnected(false);
      });

      // Simulation data handlers
      socket.on("step_data", (data) => {
        console.log("Received step data:", data);
        setSimulationData(data);
        if (data.status === "success") {
          setCurrentStep(data.current_step);
        }
      });
    }

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [serverUrl]);

  // Function to request next step manually
  const requestNextStep = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit("request_next_step");
    }
  };

  return {
    isConnected,
    simulationData,
    simulationStatus,
    currentStep,
    requestNextStep,
  };
};
