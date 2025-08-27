import useGlobalState from "@/hooks/use-global-state"

export const getCursorStyle = () => {
    const {isPanning, isDraggingNode, isDraggingUser, editMode} = useGlobalState.getState()
    if (isPanning) return "grabbing";
    if (isDraggingNode || isDraggingUser) return "grabbing";
    if (editMode === "drag") return "grab";
    if (editMode !== "none") return "move";
    return "crosshair";
}