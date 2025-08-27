import { useState } from "react";

export function useSimulationState() {
  const [users, setUsers] = useState([]);


  // UI State

  return {
    users,
    setUsers,
  };
}
