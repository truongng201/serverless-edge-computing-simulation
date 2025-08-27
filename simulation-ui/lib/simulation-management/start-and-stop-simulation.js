import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const startSimulation = async () => {
  const { setIsSimulating, setLoadingSimulation } = useGlobalState.getState();
  try {
    setLoadingSimulation(true);
    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_simulation`
    );

    if (response.data && response.data.success) {
      setIsSimulating(true);
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

    if (response.data && response.data.success) {
      setIsSimulating(false);
    }
  } catch (error) {
    console.error("Error stopping simulation:", error);
  } finally {
    setLoadingSimulation(false);
  }
};