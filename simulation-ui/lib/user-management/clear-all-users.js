import useGlobalState from "@/hooks/use-global-state";

// Backend-only cleanup used by scenario initializers
export const serverClearAllUsers = async () => {
  const { setUsers, setSelectedUser, setLastStreetSpawnAt } = useGlobalState.getState();
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/reset_simulation`, { method: 'POST' }).catch(() => {});
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_all_users`, { method: 'DELETE' }).catch(() => {});

      // Verify and hard-delete any remaining users individually
      try {
        const verify = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_all_users`);
        if (verify.ok) {
          const payload = await verify.json();
          const users = payload?.data || [];
          if (Array.isArray(users) && users.length > 0) {
            await Promise.allSettled(users.map(u => {
              const id = u?.user_id;
              if (!id) return Promise.resolve();
              return fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_user/${encodeURIComponent(id)}`, { method: 'DELETE' });
            }));
          }
        }
      } catch {}
    }
  } catch (error) {
    console.error('Error (backend-only) deleting all users:', error);
  }
  // Keep local UI context (scenario/network) intact; just clear arrays
  setUsers([]);
  setSelectedUser(null);
  setLastStreetSpawnAt(Date.now());
};

// Full clear invoked by the UI Clear button
export const clearAllUsers = async () => {
    const { 
      setUsers, 
      setSelectedUser, 
      setLastStreetSpawnAt,
      setIsSimulating,
      setSelectedScenario,
      setRoadNetwork,
    } = useGlobalState.getState();
    try {
    // Call API to delete all users if API URL is available
    if (process.env.NEXT_PUBLIC_API_URL) {
      // Reset simulation state on server to avoid auto-repopulation from datasets
      // 1) Reset simulation state on server (turn off dataset auto-populate and clear server-side user_nodes)
      await serverClearAllUsers();
    }
  } catch (error) {
    console.error('Error deleting all users from server:', error);
  }

  // Clear local state regardless of API call result
  setUsers([]);
  setSelectedUser(null);
  setLastStreetSpawnAt(Date.now());

  // Stop local spawning and street-map loop to avoid immediate repopulation
  setIsSimulating(false);
  setSelectedScenario('none');
  setRoadNetwork(null);
};
