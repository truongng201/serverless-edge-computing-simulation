import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

export const useSocket = (serverUrl = 'http://localhost:5001') => {
  const socketRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [simulationData, setSimulationData] = useState(null);
  const [simulationStatus, setSimulationStatus] = useState('stopped');
  const [currentStep, setCurrentStep] = useState(659);
  const intervalRef = useRef(null);

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(serverUrl, {
      transports: ['websocket', 'polling']
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('Connected to server');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from server');
      setIsConnected(false);
    });

    socket.on('connection_response', (data) => {
      console.log('Connection response:', data);
    });

    // Simulation data handlers
    socket.on('step_data', (data) => {
      console.log('Received step data:', data);
      setSimulationData(data);
      if (data.status === 'success') {
        setCurrentStep(data.current_step);
      }
    });

    socket.on('simulation_status', (data) => {
      console.log('Simulation status:', data);
      setSimulationStatus(data.status);
      if (data.current_step !== undefined) {
        setCurrentStep(data.current_step);
      }
    });

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      socket.disconnect();
    };
  }, [serverUrl]);

  // Function to request next step manually
  const requestNextStep = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('request_next_step');
    }
  };

  // Function to start automatic simulation (10-second intervals)
  const startAutoSimulation = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('start_simulation');
      
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      // Start new interval for requesting steps every 10 seconds
      intervalRef.current = setInterval(() => {
        if (socketRef.current && isConnected) {
          socketRef.current.emit('request_next_step');
        }
      }, 10000); // 10 seconds
    }
  };

  // Function to stop automatic simulation
  const stopAutoSimulation = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('stop_simulation');
    }
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Function to reset simulation
  const resetSimulation = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('reset_simulation');
    }
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    setSimulationData(null);
  };

  // Function to get current status
  const getCurrentStatus = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('get_current_status');
    }
  };

  return {
    isConnected,
    simulationData,
    simulationStatus,
    currentStep,
    requestNextStep,
    startAutoSimulation,
    stopAutoSimulation,
    resetSimulation,
    getCurrentStatus
  };
};
