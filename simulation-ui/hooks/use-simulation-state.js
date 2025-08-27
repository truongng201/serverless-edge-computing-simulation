import { useState } from "react";

export function useSimulationState() {
  const [users, setUsers] = useState([]);


  // UI State
  const [selectedCentral, setSelectedCentral] = useState(null);


  return {
    users,
    setUsers,
    selectedCentral,
    setSelectedCentral,
  };
}
