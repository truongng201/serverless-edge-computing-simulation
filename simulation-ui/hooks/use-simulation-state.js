import { useState } from "react";

export function useSimulationState() {
  const [users, setUsers] = useState([]);


  // UI State
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);


  return {
    users,
    setUsers,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
  };
}
