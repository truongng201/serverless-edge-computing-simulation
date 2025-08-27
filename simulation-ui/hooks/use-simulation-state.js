import { useState } from "react";

export function useSimulationState() {
  const [users, setUsers] = useState([]);


  // UI State
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);


  return {
    users,
    setUsers,
    selectedUser,
    setSelectedUser,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
  };
}
