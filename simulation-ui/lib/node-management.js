// Node Management Functions

export const addEdgeNode = (edgeNodes, edgeCoverage, setEdgeNodes) => {
  const newEdge = {
    id: `edge-${edgeNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 200) + 100,
    y: Math.random() * (window.innerHeight - 200) + 100,
    currentLoad: 0,
    coverage: edgeCoverage[0],
  };
  setEdgeNodes((prev) => [...prev, newEdge]);
};

export const removeEdgeNode = (edgeNodes, selectedEdge, setEdgeNodes, setSelectedEdge) => {
  if (edgeNodes.length > 0) {
    const nodeToRemove = edgeNodes[edgeNodes.length - 1];
    setEdgeNodes((prev) => prev.slice(0, -1));
    if (selectedEdge && selectedEdge.id === nodeToRemove.id) {
      setSelectedEdge(null);
    }
  }
};

export const addCentralNode = (centralNodes, centralCoverage, setCentralNodes) => {
  const newCentral = {
    id: `central-${centralNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 400) + 200,
    y: Math.random() * (window.innerHeight - 400) + 200,
    currentLoad: 0,
    coverage: centralCoverage[0],
  };
  setCentralNodes((prev) => [...prev, newCentral]);
};

export const removeCentralNode = (centralNodes, selectedCentral, setCentralNodes, setSelectedCentral) => {
  if (centralNodes.length > 0) {
    setCentralNodes((prev) => prev.slice(0, -1));
    if (
      selectedCentral &&
      selectedCentral.id === `central-${centralNodes.length}`
    ) {
      setSelectedCentral(null);
    }
  }
};

export const deleteSelectedNode = (
  selectedEdge, 
  selectedCentral, 
  setEdgeNodes, 
  setCentralNodes, 
  setSelectedEdge, 
  setSelectedCentral
) => {
  if (selectedEdge) {
    setEdgeNodes((prev) =>
      prev.filter((edge) => edge.id !== selectedEdge.id)
    );
    setSelectedEdge(null);
  }
  if (selectedCentral) {
    setCentralNodes((prev) =>
      prev.filter((central) => central.id !== selectedCentral.id)
    );
    setSelectedCentral(null);
  }
};

export const clearAllUsers = async (setUsers, setSelectedUser) => {
  try {
    // Call API to delete all users if API URL is available
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/delete_all_users`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        console.error('Failed to delete all users from server:', response.statusText);
      } else {
        console.log('All users deleted successfully from server');
      }
    }
  } catch (error) {
    console.error('Error deleting all users from server:', error);
  }

  // Clear local state regardless of API call result
  setUsers([]);
  setSelectedUser(null);
};
