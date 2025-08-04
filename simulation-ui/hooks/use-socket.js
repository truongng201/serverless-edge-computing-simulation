import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

export const useSocket = (
  serverUrl = "http://localhost:5000",
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
      // Connect to socket if not already connected
      if (!socketRef.current) {
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

      // Start continuous data fetching
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      intervalRef.current = setInterval(() => {
        if (socketRef.current && isConnected) {
          socketRef.current.emit("request_next_step");
        }
      }, 1000); // Request data every 1 second

      setSimulationStatus("running");
    } else {
      // Pause simulation - stop the interval but keep connection
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setSimulationStatus("paused");
    }

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [serverUrl, isSimulating, isConnected]);

  // Function to request next step manually
  const requestNextStep = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit("request_next_step");
    }
  };

  // Function to disconnect from socket
  const disconnect = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setIsConnected(false);
    setSimulationStatus("stopped");
  };

  return {
    isConnected,
    simulationData,
    simulationStatus,
    currentStep,
    requestNextStep,
    disconnect,
  };
};
