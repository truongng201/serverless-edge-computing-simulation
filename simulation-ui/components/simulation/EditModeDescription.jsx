import React from "react";
import useGlobalState from "@/hooks/use-global-state";

export default function EditModeDescription() {
  const { editMode } = useGlobalState();
  const getEditModeDescription = () => {
    switch (editMode) {
      case "nodes":
        return "Node Edit: Drag nodes to move • Click to select";
      case "users":
        return "User Edit: Drag users to move • Click to select";
      case "both":
        return "Full Edit: Drag nodes and users • Click to select";
      case "drag":
        return "Drag Mode: Drag to pan the map • Mouse wheel to zoom";
      default:
        return "Click to add users • Mouse wheel to zoom";
    }
  };
  return (
    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg text-sm z-20">
      {getEditModeDescription()}
    </div>
  );
}
