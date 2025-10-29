import axios from "axios";
import useGlobalState from "@/hooks/use-global-state";

export const loadTaxiDRoads = async () => {
  const {
    setRoads,
    setShowRoads,
    setPanOffset,
    setZoomLevel,
    canvasRef,
  } = useGlobalState.getState();

  const base = process.env.NEXT_PUBLIC_API_URL;
  const url = `${base}/api/v1/central/taxid/roads`;
  const res = await axios.get(url);
  const { roads, bounds, center } = res.data?.data || res.data || {};
  if (!roads) return;

  // Set roads for drawing
  setRoads(roads);
  setShowRoads(true);

  // Fit map into the current viewport (best-effort)
  const canvas = canvasRef.current;
  const vw = (canvas && canvas.width) || window.innerWidth || 1200;
  const vh = (canvas && canvas.height) || window.innerHeight || 800;

  const worldW = (bounds?.maxX ?? 0) - (bounds?.minX ?? 0);
  const worldH = (bounds?.maxY ?? 0) - (bounds?.minY ?? 0);
  if (worldW > 0 && worldH > 0) {
    const margin = 80;
    const scaleX = (vw - margin * 2) / worldW;
    const scaleY = (vh - margin * 2) / worldH;
    const zoom = Math.max(0.1, Math.min(scaleX, scaleY));
    setZoomLevel(zoom);
    // Pan so that center of world appears near canvas center
    const cx = center?.x ?? worldW / 2;
    const cy = center?.y ?? worldH / 2;
    const panX = vw / 2 - cx * zoom;
    const panY = vh / 2 - cy * zoom;
    setPanOffset({ x: panX, y: panY });
  }
};

