import useGlobalState from "@/hooks/use-global-state";

export const deleteSelectedUser = async () => {
  const { selectedUser, setUsers, setSelectedUser } = useGlobalState;
  if (!selectedUser) return;
  try {
    // Call API to delete user if API URL is available
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_user/${selectedUser.id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        console.error(
          "Failed to delete user from server:",
          response.statusText
        );
      }
    }
  } catch (error) {
    console.error("Error deleting user from server:", error);
  }
  setUsers((prevUsers) => {
    const newUsers = [];
    for (let i = 0; i < prevUsers.length; i++) {
      if (prevUsers[i].id !== selectedUser.id) {
        newUsers.push(prevUsers[i]);
      }
    }
    return newUsers;
  });
  setSelectedUser(null);
};
