import random
import logging
from typing import List, Tuple

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.osm_loader import load_graph, graph_bounds_meters, edge_geometries
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config


class StartTaxiDSampleController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.current_dataset = "taxid"
        # Clear existing users
        self.scheduler.user_nodes.clear()
        self.logger = logging.getLogger(__name__)

    def _update_scheduler(self):
        self.scheduler.current_dataset = self.current_dataset

    def _meters_to_pixels_transform(self, bounds: Tuple[float, float, float, float]):
        minx, miny, maxx, maxy = bounds

        def to_px(x_m: float, y_m: float) -> Tuple[float, float]:
            # Screen coordinates: x grows right, y grows down; keep north-up by flipping Y
            x_px = (x_m - minx) / Config.DEFAULT_PIXEL_TO_METERS
            y_px = (maxy - y_m) / Config.DEFAULT_PIXEL_TO_METERS
            return x_px, y_px

        # Center of bbox in pixels
        cx_m = (minx + maxx) / 2.0
        cy_m = (miny + maxy) / 2.0
        cx_px, cy_px = to_px(cx_m, cy_m)
        return to_px, (cx_px, cy_px)

    def _sample_points_on_edges(self, polylines_m: List[List[Tuple[float, float]]], n: int) -> List[Tuple[float, float]]:
        """Sample n points along provided meter-space polylines."""
        pts: List[Tuple[float, float]] = []
        if not polylines_m:
            return pts
        for _ in range(n):
            line = random.choice(polylines_m)
            if len(line) < 2:
                continue
            i = random.randint(0, len(line) - 2)
            (x0, y0), (x1, y1) = line[i], line[i + 1]
            t = random.random()
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            pts.append((x, y))
        return pts

    def execute(self):
        self._update_scheduler()

        # Load graph (projected), compute bounds and transform
        self.logger.info(
            f"TaxiD: loading graph xml='{Config.TAXID_OSM_XML_PATH}' graphml='{Config.TAXID_GRAPHML_PATH}'"
        )
        G = load_graph(
            xml_path=Config.TAXID_OSM_XML_PATH,
            graphml_path=Config.TAXID_GRAPHML_PATH,
            project=True,
        )
        bounds_m = graph_bounds_meters(G)
        to_px, (cx_px, cy_px) = self._meters_to_pixels_transform(bounds_m)

        # Optionally re-center central node to bbox center (for better initial view)
        self.scheduler.central_node["location"] = {"x": cx_px, "y": cy_px}

        # Collect edge polylines (meters)
        polylines_m: List[List[Tuple[float, float]]] = []
        for coords, data in edge_geometries(G):
            # Filter to road-like edges; keep drivable roads primarily
            hwy = data.get("highway")
            # highway can be list or string
            hwys = set(hwy if isinstance(hwy, list) else [hwy]) if hwy else set()
            allowed = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified"}
            if not hwys or hwys & allowed:
                polylines_m.append(coords)

        # Sample user spawn points along roads (meters)
        spawn_count = 40
        spawn_m = self._sample_points_on_edges(polylines_m, spawn_count)
        self.logger.info(
            f"TaxiD: sampled {len(spawn_m)} user points from {len(polylines_m)} road polylines"
        )

        # Create users at sampled points (convert to pixels for UI/scheduler)
        for idx, (xm, ym) in enumerate(spawn_m):
            xp, yp = to_px(xm, ym)

            # Latency defaults; assignment and propagation will be updated on node_assignment()
            data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
            bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
            transmission_delay = data_size / bandwidth

            latency = Latency(
                distance=0.0,
                data_size=data_size,
                bandwidth=bandwidth,
                propagation_delay=0.0,
                transmission_delay=transmission_delay,
                computation_delay=0.0,
                container_status="unknown",
                total_turnaround_time=transmission_delay,
            )

            user_node = UserNodeInfo(
                user_id=f"taxid_user_{idx}",
                assigned_node_id=None,
                location={"x": xp, "y": yp},
                last_executed=0,
                size=8,
                speed=5,
                latency=latency,
            )
            self.scheduler.create_user_node(user_node)

        # Compute initial assignment and update latencies
        self.scheduler.node_assignment()
        self.logger.info(
            f"TaxiD: created {len(self.scheduler.user_nodes)} users; central at {self.scheduler.central_node['location']}"
        )
