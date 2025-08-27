import useGlobalState from "@/hooks/use-global-state";

export const removeEdgeNode = () => {
  const { edgeNodes, selectedEdge, setEdgeNodes, setSelectedEdge } =
    useGlobalState.getState();
  if (edgeNodes.length > 0) {
    const nodeToRemove = edgeNodes[edgeNodes.length - 1];
    setEdgeNodes((prev) => prev.slice(0, -1));
    if (selectedEdge && selectedEdge.id === nodeToRemove.id) {
      setSelectedEdge(null);
    }
  }
};