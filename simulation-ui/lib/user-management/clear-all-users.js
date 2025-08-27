import useGlobalState from "@/hooks/use-global-state";

export const clearAllUsers = async () => {
    const {setUsers, setSelectedUser} = useGlobalState.getState()
    try {
    // Call API to delete all users if API URL is available
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_all_users`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        console.error('Failed to delete all users from server:', response.statusText);
      }
    }
  } catch (error) {
    console.error('Error deleting all users from server:', error);
  }

  // Clear local state regardless of API call result
  setUsers([]);
  setSelectedUser(null);
};
