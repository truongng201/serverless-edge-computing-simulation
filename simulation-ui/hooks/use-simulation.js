import { useEffect, useRef, useState } from "react";
import axios from "axios";

export const useSimulation = (
  serverUrl = "http://localhost:5001",
  isSimulating,
  simulationSpeed = 1,
  setUsers
) => {
  const [simulationStatus, setSimulationStatus] = useState("stopped");
  const [currentStep, setCurrentStep] = useState(28800.00); // Starting timestep
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const stepInterval = 300; // 5 minutes in seconds (300 seconds)

  // Function to fetch simulation data for a specific timestep
  const fetchSimulationData = async (timestep) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log(`Fetching simulation data for timestep: ${timestep}`);
      
      const response = await axios.get(`${serverUrl}/get_sample`, {
        params: { timestep: timestep }
      });
      
      if (response.data.status === "success") {
        console.log(`Successfully fetched data for timestep ${timestep}:`, response.data.data);
        setUsers(response.data.data?.items);
        setCurrentStep(timestep);
        return response.data.data;
      } else {
        throw new Error(response.data.message || "Failed to fetch data");
      }
    } catch (err) {
      console.error("Error fetching simulation data:", err);
      setError(err.message || "Failed to fetch simulation data");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  // Effect to handle simulation start/stop
  useEffect(() => {
    if (isSimulating) {
      console.log(`Starting simulation with speed ${simulationSpeed}x`);
      
      // Start continuous data fetching
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      // Fetch initial data immediately
      fetchSimulationData(currentStep);
      
      // Set up interval to fetch data - speed affects interval duration
      const intervalDuration = Math.max(100, 1000 / simulationSpeed); // Minimum 100ms
      
      intervalRef.current = setInterval(() => {
        setCurrentStep(prevStep => {
          const nextStep = prevStep + stepInterval;
          console.log(`Moving to next timestep: ${nextStep}`);
          fetchSimulationData(nextStep);
          return nextStep;
        });
      }, intervalDuration);

      setSimulationStatus("running");
    } else {
      console.log("Pausing simulation");
      // Pause simulation - stop the interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setSimulationStatus("paused");
    }

    // Cleanup on unmount or when simulation stops
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isSimulating, simulationSpeed, serverUrl]);

  // Function to request next step manually
  const requestNextStep = async () => {
    const nextStep = currentStep + stepInterval;
    const data = await fetchSimulationData(nextStep);
    return data;
  };

  // Function to reset simulation to initial state
  const resetSimulation = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setCurrentStep(28800.00); // Reset to initial timestep
    setUsers([]);
    setSimulationStatus("stopped");
    setError(null);
  };

  // Function to jump to a specific timestep
  const jumpToTimestep = async (timestep) => {
    const data = await fetchSimulationData(timestep);
    return data;
  };

  return {
    isConnected: true, // Always connected for REST API
    simulationStatus,
    currentStep,
    isLoading,
    error,
    requestNextStep,
    resetSimulation,
    jumpToTimestep,
    fetchSimulationData,
  };
};
