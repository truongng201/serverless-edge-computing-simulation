import useGlobalState from "@/hooks/use-global-state";

export const updateEdgeCoverage = async (newCoverage) => {
  const {
    selectedEdge,
    setEdgeNodes,
    setEdgeCoverage,
    setSelectedEdge,
    edgeNodes,
  } = useGlobalState.getState();
  setEdgeCoverage(newCoverage);
  try {
    if (!selectedEdge) {
      // No edge node selected
      return;
    }

    const updatedEdgeNodes = edgeNodes.map((node) =>
      node.id === selectedEdge.id ? { ...node, coverage: newCoverage[0] } : node
    );
    setEdgeNodes(updatedEdgeNodes);
    setSelectedEdge({ ...selectedEdge, coverage: newCoverage[0] });

    const payload = {
      node_id: selectedEdge.id,
      coverage: parseFloat(newCoverage[0]),
      location: {
        x: Math.round(selectedEdge.x),
        y: Math.round(selectedEdge.y),
      },
    };

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/update_edge_node`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Error response:", errorText);
    }
  } catch (error) {
    console.error("Error updating edge node coverage:", error);
  }
};
