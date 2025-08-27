import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const getDactSample = async () => {
  const { userSize, setUsers, setLoadingData, setDataError } =
    useGlobalState.getState();

  try {
    setLoadingData(true);
    const response = await axios.get(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_dact_sample`
    );

    if (response.data && response.data.success && response.data.users) {
      const dactUsers = response.data.users.map((user, index) => ({
        id: user.user_id || `dact_user_${index}`,
        x: user.location.x || Math.random() * 800,
        y: user.location.y || Math.random() * 600,
        vx: 0,
        vy: 0,
        assignedEdge: user.assigned_edge || null,
        assignedCentral: user.assigned_central || null,
        assignedNodeID: user.assigned_node_id || null,
        latency: user.latency || 0,
        size: user.size || userSize[0] || 10,
        last_executed_period: user.last_executed_period || null,
      }));
      setUsers(dactUsers);
    }
  } catch (error) {
    setDataError(`Failed to get DACT sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};

export const getVehicleSample = async () => {
  const { userSize, setUsers, setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    const response = await axios.get(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_vehicles_sample`
    );


    if (response.data && response.data.success && response.data.users) {
      const vehicleUsers = response.data.users.map((user, index) => ({
        id: user.user_id || `vehicle_user_${index}`,
        x: user.location.x || Math.random() * 800,
        y: user.location.y || Math.random() * 600,
        vx: 0,
        vy: 0,
        assignedEdge: user.assigned_edge || null,
        assignedCentral: user.assigned_central || null,
        assignedNodeID: user.assigned_node_id || null,
        latency: user.latency || 0,
        size: user.size || userSize[0] || 10,
        last_executed_period: user.last_executed_period || null,
      }));
      setUsers(vehicleUsers);
    }
  } catch (error) {
    setDataError(`Failed to get Vehicle sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
