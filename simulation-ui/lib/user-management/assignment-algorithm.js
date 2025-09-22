import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";
export const getCurrentAssignmentAlgorithm = async () => {
  const { setAssignmentAlgorithm } = useGlobalState.getState();
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment_algorithm`
      );
      if (response.data && response.data?.status === "success") {
        const algorithm = response.data?.data?.algorithm;
        setAssignmentAlgorithm(algorithm);
      }
    }
  } catch (error) {
    console.error("Error fetching assignment algorithm:", error);
  }
};

export const getAllAssignmentAlgorithms = async () => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/all_assignment_algorithms`
      );
      if (response.data && response.data?.status === "success") {
        return response.data?.data?.algorithms || [];
      }
    }
  } catch (error) {
    console.error("Error fetching all assignment algorithms:", error);
  }
};

export const setServerAssignmentAlgorithm = async (selectedAlgorithm) => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/assignment_algorithm`,
        {
          algorithm: selectedAlgorithm,
        }
      );
      if (!response.ok || response.data?.status !== "success") {
        console.error("Failed to set assignment algorithm on backend");
      }
    }
  } catch (error) {
    console.error("Error setting assignment algorithm:", error);
  }
  return null;
};
