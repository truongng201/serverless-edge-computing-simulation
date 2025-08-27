import useGlobalState from "@/hooks/use-global-state";

export const deleteSelectedNode = () => {
  const {
    selectedEdge,
    selectedCentral,
    setEdgeNodes,
    setCentralNodes,
    setSelectedEdge,
    setSelectedCentral,
  } = useGlobalState.getState();
  if (selectedEdge) {
    setEdgeNodes((prev) => prev.filter((edge) => edge.id !== selectedEdge.id));
    setSelectedEdge(null);
  }
  if (selectedCentral) {
    setCentralNodes((prev) =>
      prev.filter((central) => central.id !== selectedCentral.id)
    );
    setSelectedCentral(null);
  }
};
