import useGlobalState from "@/hooks/use-global-state";

export const addCentralNode = () => {
  const { centralNodes, centralCoverage, setCentralNodes } =
    useGlobalState.getState();
  const newCentral = {
    id: `central-${centralNodes.length + 1}`,
    x: Math.random() * (window.innerWidth - 400) + 200,
    y: Math.random() * (window.innerHeight - 400) + 200,
    currentLoad: 0,
    coverage: centralCoverage[0],
  };
  setCentralNodes((prev) => [...prev, newCentral]);
};
