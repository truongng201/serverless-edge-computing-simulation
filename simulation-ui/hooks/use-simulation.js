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
  const stepInterval = 1

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
        // Update users with the fetched data - handle both array and object with items property
        const userData = response.data.data?.items || response.data.data || [];
        
        // Instead of replacing all users, update existing ones and add new ones
        setUsers(prevUsers => {
          const userMap = new Map();
          
          // First, add all existing users to the map
          prevUsers.forEach(user => {
            userMap.set(user.id, user);
          });
          
          // Then update with new data or add new users
          userData.forEach(newUserData => {
            const existingUser = userMap.get(newUserData.id);
            if (existingUser) {
              // Update existing user with new position and data, preserving other properties
              userMap.set(newUserData.id, {
                ...existingUser,
                ...newUserData,
                // Preserve UI-specific properties that might not come from API
                manualConnection: existingUser.manualConnection,
                latency: existingUser.latency || 0,
                vx: existingUser.vx || 0,
                vy: existingUser.vy || 0,
                assignedRoad: existingUser.assignedRoad,
                roadDirection: existingUser.roadDirection,
                constrainedToRoad: existingUser.constrainedToRoad
              });
            } else {
              // Add new user with default properties
              userMap.set(newUserData.id, {
                ...newUserData,
                manualConnection: false,
                latency: 0,
                vx: (Math.random() - 0.5) * 2,
                vy: (Math.random() - 0.5) * 2,
                assignedRoad: null,
                roadDirection: 1,
                constrainedToRoad: false
              });
            }
          });
          
          // Remove users that are no longer in the data
          const currentUserIds = new Set(userData.map(u => u.id));
          const updatedUsers = Array.from(userMap.values()).filter(user => 
            currentUserIds.has(user.id)
          );
          
          return updatedUsers;
        });
        
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
      setSimulationStatus("running");
      
      // Start continuous data fetching
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      // Fetch initial data immediately
      fetchSimulationData(currentStep);
      
      // Set up interval to fetch data every 5 seconds, adjusted by simulation speed
      const baseIntervalDuration = 5000; // 5 seconds
      const intervalDuration = Math.max(1000, baseIntervalDuration / simulationSpeed); // Minimum 1 second
      
      console.log(`Setting up interval every ${intervalDuration}ms (${intervalDuration/1000}s)`);
      
      intervalRef.current = setInterval(() => {
        setCurrentStep(prevStep => {
          const nextStep = prevStep + stepInterval;
          console.log(`Moving to next timestep: ${nextStep}`);
          fetchSimulationData(nextStep);
          return nextStep;
        });
      }, intervalDuration);

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
  }, [isSimulating, simulationSpeed, serverUrl, currentStep]);

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
