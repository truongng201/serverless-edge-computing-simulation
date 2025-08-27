import useGlobalState from "@/hooks/use-global-state";

export const removeCentralNode = () => {
  const { centralNodes, selectedCentral, setCentralNodes, setSelectedCentral } =
    useGlobalState.getState();
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
