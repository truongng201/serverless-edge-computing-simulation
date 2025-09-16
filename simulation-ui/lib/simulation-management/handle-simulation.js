import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const startSimulation = async () => {
  const { setIsSimulating, setLoadingSimulation } = useGlobalState.getState();
  try {
    setLoadingSimulation(true);
    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_simulation`
    );

    if (response.data && response.data.status === "success") {
      setIsSimulating(true);
      // Frontend assignment removed; backend handoff will take over
    }
  } catch (error) {
    console.error("Error starting simulation:", error);
  } finally {
    setLoadingSimulation(false);
  }
};


export const stopSimulation = async () => {
  const { setIsSimulating, setLoadingSimulation } = useGlobalState.getState();

  try {
    setLoadingSimulation(true);
    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/stop_simulation`
    );

    if (response.data && response.data.status === "success") {
      setIsSimulating(false);
    }
  } catch (error) {
    console.error("Error stopping simulation:", error);
  } finally {
    setLoadingSimulation(false);
  }
};


export const resetSimulation = async () => {
  const { setIsSimulating, setLoadingSimulation } = useGlobalState.getState();

  try {
    setLoadingSimulation(true);
    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/reset_simulation`
    );

    if (response.data && response.data.status === "success") {
      setIsSimulating(false);
    }
  } catch (error) {
    console.error("Error reset simulation:", error);
  } finally {
    setLoadingSimulation(false);
  }
};
