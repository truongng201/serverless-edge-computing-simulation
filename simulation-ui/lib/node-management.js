// Node Management Functions

export const addEdgeNode = (edgeNodes, edgeCapacity, edgeCoverage, setEdgeNodes) => {
  const newEdge = {
    id: `edge-${edgeNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 200) + 100,
    y: Math.random() * (window.innerHeight - 200) + 100,
    capacity: edgeCapacity[0],
    currentLoad: 0,
    replicas: [],
    coverage: edgeCoverage[0],
    isWarm: false,
    lastAccessTime: null,
    lastMetrics: null,
    type: "cloudlet"
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

export const addCentralNode = (centralNodes, centralCapacity, centralCoverage, setCentralNodes) => {
  const newCentral = {
    id: `central-${centralNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 400) + 200,
    y: Math.random() * (window.innerHeight - 400) + 200,
    capacity: centralCapacity[0],
    currentLoad: 0,
    coverage: centralCoverage[0],
    type: "main",
    isWarm: false,
    lastAccessTime: null,
    lastMetrics: null,
    nodeType: "cloud"
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

export const clearAllUsers = (setUsers, setSelectedUser) => {
  setUsers([]);
  setSelectedUser(null);
};

export const clearAllEdgeNodes = (setEdgeNodes, setSelectedEdge) => {
  setEdgeNodes([]);
  setSelectedEdge(null);
};

export const clearAllCentralNodes = (setCentralNodes, setSelectedCentral) => {
  setCentralNodes([]);
  setSelectedCentral(null);
};

export const clearEverything = (
  setUsers,
  setEdgeNodes,
  setCentralNodes,
  setSelectedUser,
  setSelectedEdge,
  setSelectedCentral,
  setIsSimulating,
  setTotalLatency
) => {
  setUsers([]);
  setEdgeNodes([]);
  setCentralNodes([]);
  setSelectedUser(null);
  setSelectedEdge(null);
  setSelectedCentral(null);
  setIsSimulating(false);
  setTotalLatency(0);
};

export const resetSimulation = (clearEverything) => {
  clearEverything();
};
