
import axios from "axios";

export const useSimulation = (serverUrl = "http://localhost:5001", setUsers) => {
  // Fetch sample data for a given endpoint and params
  const getSampleData = async (endpoint = "/get_sample", params = {}) => {
    try {
      const response = await axios.get(`${serverUrl}${endpoint}`, { params });
      if (response.data.status === "success") {
        const userData = response.data.data?.items || response.data.data || [];
        setUsers(prevUsers => {
          const userMap = new Map();
          prevUsers.forEach(user => {
            userMap.set(user.id, user);
          });
          userData.forEach(newUserData => {
            const existingUser = userMap.get(newUserData.id);
            if (existingUser) {
              userMap.set(newUserData.id, {
                ...existingUser,
                ...newUserData,
                manualConnection: existingUser.manualConnection,
                latency: existingUser.latency || 0,
                vx: existingUser.vx || 0,
                vy: existingUser.vy || 0,
                assignedRoad: existingUser.assignedRoad,
                roadDirection: existingUser.roadDirection,
                constrainedToRoad: existingUser.constrainedToRoad
              });
            } else {
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
          const currentUserIds = new Set(userData.map(u => u.id));
          const updatedUsers = Array.from(userMap.values()).filter(user => currentUserIds.has(user.id));
          return updatedUsers;
        });
        return response.data.data;
      } else {
        throw new Error(response.data.message || "Failed to fetch data");
      }
    } catch (err) {
      console.error("Error fetching sample data:", err);
      return null;
    }
  };

  // Helper for DACT sample
  const getDactSample = async (params = {}) => {
    return getSampleData("/get_dact_sample", params);
  };

  return { getSampleData, getDactSample };
};
