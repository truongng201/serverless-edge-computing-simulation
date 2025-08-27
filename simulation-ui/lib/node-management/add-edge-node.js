import useGlobalState from "@/hooks/use-global-state";

export const addEdgeNode = () => {
  const { edgeNodes, setEdgeNodes, edgeCoverage } = useGlobalState.getState();
  const newEdge = {
    id: `edge-${edgeNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 200) + 100,
    y: Math.random() * (window.innerHeight - 200) + 100,
    currentLoad: 0,
    coverage: edgeCoverage[0],
  };
  setEdgeNodes((prev) => [...prev, newEdge]);
};
