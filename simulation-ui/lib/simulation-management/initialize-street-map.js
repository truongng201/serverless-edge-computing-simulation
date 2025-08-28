import useGlobalState from "@/hooks/use-global-state";
import { clearAllUsers } from "@/lib/user-management";
import { generateSaigonRoadNetwork } from "@/lib/road-network";
import { generateStreetMapUsers } from "@/lib/street-map-users";

export const initializeStreetMap = async () => {
  const {
    setLoadingData,
    setDataError,
    setRoadNetwork,
    setUsers,
    userSpeed,
    userSize,
  } = useGlobalState.getState();

  try {
    setLoadingData(true);
    setDataError("");

    // Clear existing users from backend first
    await clearAllUsers();

    // Generate Saigon road network
    const newRoadNetwork = generateSaigonRoadNetwork(1200, 800); // Adjust to canvas size
    setRoadNetwork(newRoadNetwork);

    // Generate initial street map users
    const streetUsers = generateStreetMapUsers(
      newRoadNetwork,
      8, // initial user count (reduced for better performance)
      userSpeed[0],
      userSize[0]
    );
    setUsers(streetUsers);
  } catch (error) {
    console.error("Error initializing street map scenario:", error);
    setDataError(`Failed to initialize street map: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
