from typing import Any, Dict, List, Tuple

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.osm_loader import load_graph, graph_bounds_meters, edge_geometries

from config import Config


class GetTaxiDRoadsController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler

    def _meters_to_pixels_transform(self, bounds: Tuple[float, float, float, float]):
        minx, miny, maxx, maxy = bounds

        def to_px(x_m: float, y_m: float) -> Tuple[float, float]:
            x_px = (x_m - minx) / Config.DEFAULT_PIXEL_TO_METERS
            y_px = (maxy - y_m) / Config.DEFAULT_PIXEL_TO_METERS
            return x_px, y_px

        cx_m = (minx + maxx) / 2.0
        cy_m = (miny + maxy) / 2.0
        cx_px, cy_px = to_px(cx_m, cy_m)
        width_m = maxx - minx
        height_m = maxy - miny
        width_px = width_m / Config.DEFAULT_PIXEL_TO_METERS
        height_px = height_m / Config.DEFAULT_PIXEL_TO_METERS

        return to_px, {"minX": 0.0, "minY": 0.0, "maxX": width_px, "maxY": height_px}, {"x": cx_px, "y": cy_px}

    def execute(self) -> Dict[str, Any]:
        # Load and project graph
        G = load_graph(
            xml_path=Config.TAXID_OSM_XML_PATH,
            graphml_path=Config.TAXID_GRAPHML_PATH,
            project=True,
        )
        bounds_m = graph_bounds_meters(G)
        to_px, bounds_px, center_px = self._meters_to_pixels_transform(bounds_m)

        # Prepare simplified road polylines
        roads: List[List[List[float]]] = []
        allowed = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified"}
        for coords, data in edge_geometries(G):
            hwy = data.get("highway")
            hwys = set(hwy if isinstance(hwy, list) else [hwy]) if hwy else set()
            if not hwys or hwys & allowed:
                poly_px = [list(to_px(x, y)) for x, y in coords]
                roads.append(poly_px)

        return {
            "bounds": bounds_px,
            "center": center_px,
            "pixel_per_meter": 1.0 / Config.DEFAULT_PIXEL_TO_METERS,
            "roads": roads,
        }

