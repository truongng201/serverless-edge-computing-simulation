import { useState } from "react";

export function useSimulationState() {
  const [users, setUsers] = useState([]);
  const [centralNodes, setCentralNodes] = useState([]);


  // UI State
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedCentral, setSelectedCentral] = useState(null);

  // Central node settings
  const [centralCoverage, setCentralCoverage] = useState([0]);

  // User Assignment state
  const [assignmentAlgorithm, setAssignmentAlgorithm] = useState("nearest-distance");


  return {
    users,
    setUsers,
    centralNodes,
    setCentralNodes,
    selectedUser,
    setSelectedUser,
    selectedEdge,
    setSelectedEdge,
    selectedCentral,
    setSelectedCentral,
    centralCoverage,
    setCentralCoverage,
    assignmentAlgorithm,
    setAssignmentAlgorithm,
  };
}
