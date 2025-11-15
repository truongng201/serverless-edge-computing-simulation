import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import pandas as pd

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.osm_loader import (
    load_graph,
    graph_bounds_meters,
)
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config


class StartTaxiDReplaySampleController:
    """
    Spawn users based on pre-exported Phase B trajectories (last N trips).

    This controller expects a pickle created by:
      serverless-sim/scripts/export_taxid_replay_last1k.py

    Each trajectory entry is:
      {"trip_id": str, "points": [{"ts": iso_str, "x_m": float, "y_m": float}, ...]}

    The controller:
      * Loads Beijing OSM graph (same as TaxiD sample)
      * Builds a meters->pixels transform
      * Creates one user per trajectory at the first point
      * Stores all trajectories (in pixels) under scheduler.current_dataset
        for later replay by get_all_users controller.
    """

    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler
        self.current_dataset = "taxid_replay"
        # Clear existing users
        self.scheduler.user_nodes.clear()
        self.logger = logging.getLogger(__name__)

    def _update_scheduler(self) -> None:
        self.scheduler.current_dataset = self.current_dataset

    def _meters_to_pixels_transform(
        self, bounds: Tuple[float, float, float, float]
    ):
        minx, miny, maxx, maxy = bounds

        def to_px(x_m: float, y_m: float) -> Tuple[float, float]:
            x_px = (x_m - minx) / Config.DEFAULT_PIXEL_TO_METERS
            y_px = (maxy - y_m) / Config.DEFAULT_PIXEL_TO_METERS
            return x_px, y_px

        cx_m = (minx + maxx) / 2.0
        cy_m = (miny + maxy) / 2.0
        cx_px, cy_px = to_px(cx_m, cy_m)
        return to_px, (cx_px, cy_px)

    def _load_replay_trajectories(self) -> List[Dict[str, Any]]:
        """
        Load trajectories exported by export_taxid_replay_last1k.py.

        Path is configurable via env if needed; by default we use
        serverless-sim/mock_data/taxid_replay_last1k.pkl under repo root.
        """
        default_path = (
            Path(__file__)
            .resolve()
            .parents[3]
            / "mock_data"
            / "taxid_replay_last1k.pkl"
        )
        path_str = getattr(
            Config,
            "TAXID_REPLAY_PATH",
            str(default_path),
        )
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(
                f"TaxiD replay pickle not found at '{path}'. "
                f"Run export_taxid_replay_last1k.py first."
            )
        self.logger.info(f"TaxiD replay: loading trajectories from '{path}'")
        trajectories = pd.read_pickle(path)
        if not isinstance(trajectories, list):
            raise ValueError("Replay pickle must contain a list of trajectories")
        return trajectories

    def execute(self) -> None:
        self._update_scheduler()

        # Load Beijing graph (projected) and derive bounds for meter->pixel map
        self.logger.info(
            f"TaxiD replay: loading graph xml='{Config.TAXID_OSM_XML_PATH}' "
            f"graphml='{Config.TAXID_GRAPHML_PATH}'"
        )
        G = load_graph(
            xml_path=Config.TAXID_OSM_XML_PATH,
            graphml_path=Config.TAXID_GRAPHML_PATH,
            project=True,
        )
        bounds_m = graph_bounds_meters(G)
        to_px, (cx_px, cy_px) = self._meters_to_pixels_transform(bounds_m)

        # Recentre central node for better initial view
        self.scheduler.central_node["location"] = {"x": cx_px, "y": cy_px}

        trajectories = self._load_replay_trajectories()
        trajectories_px: Dict[str, List[Dict[str, float]]] = {}

        # Create one user per trajectory at the first point
        for idx, traj in enumerate(trajectories):
            trip_id = str(traj.get("trip_id", idx))
            pts = traj.get("points", [])
            if not pts:
                continue
            first = pts[0]
            xm = float(first["x_m"])
            ym = float(first["y_m"])
            xp, yp = to_px(xm, ym)

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

            user_id = f"taxid_replay_{idx}"
            user_node = UserNodeInfo(
                user_id=user_id,
                assigned_node_id=None,
                location={"x": xp, "y": yp},
                last_executed=0,
                size=8,
                speed=5,
                latency=latency,
            )
            self.scheduler.create_user_node(user_node)

            # Store full trajectory in pixel space for later replay
            seq_px: List[Dict[str, float]] = []
            for pt in pts:
                xmp = float(pt["x_m"])
                ymp = float(pt["y_m"])
                px, py = to_px(xmp, ymp)
                seq_px.append({"ts": pt["ts"], "x": px, "y": py})
            trajectories_px[user_id] = seq_px

        self.scheduler.current_dataset = {
            "name": "taxid_replay",
            "trajectories_px": trajectories_px,
            "step": 0,
        }
        self.logger.info(
            f"TaxiD replay: created {len(self.scheduler.user_nodes)} users from "
            f"{len(trajectories_px)} trajectories"
        )

