import random
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import pandas as pd


from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager
from central_node.control_layer.models import Latency, UserNodeInfo
from central_node.control_layer.helper_module.osm_loader import load_graph, graph_bounds_meters, edge_geometries

from shared.custom_exception import InvalidDataException
from config import Config



class SetDatasetController:
    def __init__(self, scheduler: Scheduler, data_manager: DataManager, request_data: dict):
        self.scheduler = scheduler
        self.data_manager = data_manager
        self.request_data = request_data
        self.dataset_name = self.request_data.get("dataset_name", "none")
        self.sample_size = self.request_data.get("sample_size", None)
        self.scheduler.clear_all_users()
        self._validate()
        self.logger = logging.getLogger(__name__)


    def _validate(self):
        if self.dataset_name and self.dataset_name not in ["none", "dact", "random_generated", "taxiD", "taxiD_Replay"]:
            raise InvalidDataException(f"Dataset {self.dataset_name} is not available.")

        if self.sample_size is not None and (not isinstance(self.sample_size, int) or self.sample_size <= 0):
            raise InvalidDataException("Sample size must be a positive integer.")
        
        
    def _to_px(self, x_m: float, y_m: float, minx: float, maxy: float):
        x_px = (x_m - minx) / Config.DEFAULT_PIXEL_TO_METERS
        y_px = (maxy - y_m) / Config.DEFAULT_PIXEL_TO_METERS
        return x_px, y_px
    
    
    def _meters_to_pixels_transform(self, minx: float, miny: float, maxx: float, maxy: float):
        cx_m = (minx + maxx) / 2.0
        cy_m = (miny + maxy) / 2.0
        cx_px, cy_px = self._to_px(cx_m, cy_m, minx, maxy)
        return cx_px, cy_px

    
    def _sample_points_on_edges(self, polylines_m: List[List[Tuple[float, float]]], n: int) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = []
        if not polylines_m:
            return pts
        for idx in range(n):
            line = random.choice(polylines_m)
            if len(line) < 2:
                continue
            i = random.randint(0, len(line) - 2)
            (x0, y0), (x1, y1) = line[i], line[i + 1]
            t = random.random()
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            pts.append({
                'id': f'taxid_{idx}',
                'x': x,
                'y': y
            })
        return pts
    
    
    def _load_replay_trajectories(self) -> List[Dict[str, Any]]:
        """
        Load trajectories exported by export_taxid_replay_last1k.py.

        Supports two file formats:
        1. Basic: ts, x_m, y_m only (features recomputed by scheduler)
        2. With features: ts, x_m, y_m, v, a, delta_v, etc. (features used directly)

        Path is configurable via env; tries features file first, then basic file.
        """
        mock_data_dir = Path(__file__).resolve().parents[3] / "mock_data"
        
        # Try to find the best available file (prefer features version)
        candidates = [
            mock_data_dir / "taxid_replay_5000_features.pkl",
        ]
        
        # Allow override via config
        config_path = getattr(Config, "TAXID_REPLAY_PATH", None)
        if config_path:
            candidates.insert(0, Path(config_path))
        
        path = None
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        
        if path is None:
            raise FileNotFoundError(
                f"TaxiD replay pickle not found. Tried: {[str(c) for c in candidates[:3]]}. "
                f"Run export_taxid_replay_last1k.py first."
            )
        
        self.logger.info(f"TaxiD replay: loading trajectories from '{path}'")
        trajectories = pd.read_pickle(path)
        if not isinstance(trajectories, list):
            raise ValueError("Replay pickle must contain a list of trajectories")
        
        # Check if features are included
        if trajectories and trajectories[0].get("points"):
            first_point = trajectories[0]["points"][0]
            has_features = "v" in first_point
            self.logger.info(f"TaxiD replay: features included = {has_features}")
        
        return trajectories
    
        
    def start_sample_data(self):
        sample_data = {}
        if self.dataset_name == "dact":
            self.scheduler.set_current_step_id(659)
            sample_data = self.data_manager.get_dact_data_by_step(self.scheduler.get_current_step_id())
        elif self.dataset_name == "random_generated":
            self.scheduler.set_current_step_id(1)
            self.scheduler.set_sample_size(self.sample_size)
            sample_data = self.data_manager.get_random_generated_data(self.scheduler.get_current_step_id(), self.scheduler.get_sample_size())
        elif self.dataset_name in ["taxiD", "taxiD_Replay"]:
            current_graph = load_graph(
                xml_path=Config.TAXID_OSM_XML_PATH,
                graphml_path=Config.TAXID_GRAPHML_PATH,
                project=True,
            )
            bounds_m = graph_bounds_meters(current_graph)
            minx, miny, maxx, maxy = bounds_m
            cx_px, cy_px = self._meters_to_pixels_transform(minx, miny, maxx, maxy)
            
            # Optionally re-center central node to bbox center (for better initial view)
            self.scheduler.central_node["location"] = {"x": cx_px, "y": cy_px}
            
            if self.dataset_name == "taxiD":
                # Collect edge polylines (meters)
                polylines_m: List[List[Tuple[float, float]]] = []
                for coords, data in edge_geometries(current_graph):
                    # Filter to road-like edges; keep drivable roads primarily
                    hwy = data.get("highway")
                    # highway can be list or string
                    hwys = set(hwy if isinstance(hwy, list) else [hwy]) if hwy else set()
                    allowed = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified"}
                    if not hwys or hwys & allowed:
                        polylines_m.append(coords)
                spawn_count = 40
                sample_data["items"] = self._sample_points_on_edges(polylines_m, spawn_count)
            elif self.dataset_name == "taxiD_Replay":
                trajectories = self._load_replay_trajectories()
                # Apply sample_size limit if specified
                if self.sample_size is not None and self.sample_size < len(trajectories):
                    trajectories = trajectories[:self.sample_size]
                    self.logger.info(f"TaxiD replay: limiting to {self.sample_size} trajectories")
                trajectories_px: Dict[str, List[Dict[str, float]]] = {}
                items = []
                
                # Feature columns to copy if available
                feature_cols = ["v", "a", "delta_v", "delta_heading", 
                               "tod_sin", "tod_cos", "dow_sin", "dow_cos",
                               "rush_hour", "stop_flag", "dw_time",
                               # Optional graph-context features (present if replay export included them)
                               "node_degree", "is_junction"]
                
                for idx, traj in enumerate(trajectories):
                    trip_id = str(traj.get("trip_id", idx))
                    pts = traj.get("points", [])
                    if not pts:
                        continue
                    first = pts[0]
                    xm = float(first["x_m"])
                    ym = float(first["y_m"])
                    xp, yp = self._to_px(xm, ym, minx, maxy)
                    user_id = f"taxid_replay_{trip_id}"
                    items.append({
                        "id": user_id,
                        "x": xp,
                        "y": yp,
                    })
                    # Store full trajectory in pixel space for later replay
                    # Include features if they exist in the source data
                    seq_px: List[Dict[str, float]] = []
                    for pt in pts:
                        xmp = float(pt["x_m"])
                        ymp = float(pt["y_m"])
                        px, py = self._to_px(xmp, ymp, minx, maxy)
                        point_data = {"ts": pt["ts"], "x": px, "y": py}
                        
                        # Copy features if available (from --include-features export)
                        for feat in feature_cols:
                            if feat in pt:
                                point_data[feat] = float(pt[feat])
                        
                        seq_px.append(point_data)
                    trajectories_px[f"user_{user_id}"] = seq_px
                sample_data["items"] = items
                self.scheduler.set_trajectories_px(trajectories_px)
                self.scheduler.set_current_step_id(0)
                
        for item in sample_data.get("items", []):
            user_id = item.get("id")
            user_node = self.scheduler.get_user_by_id(user_id)
            if user_node:
                continue

            location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
            data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
            bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
            transmission_delay = data_size / bandwidth
            total_turnaround_time = transmission_delay
            latency = Latency(
                distance=0,
                data_size=data_size,
                bandwidth=bandwidth,
                propagation_delay=0.0,
                transmission_delay=transmission_delay,
                computation_delay=0.0,
                container_status="unknown",
                total_turnaround_time=total_turnaround_time
            )
            user_node = UserNodeInfo(
                user_id=f"user_{user_id}",
                assigned_node_id=None,
                location=location,
                last_executed=0,
                size=item.get("size", 10),  # Default size if not provided
                speed=item.get("speed", 5),  # Default speed if not provided
                latency=latency
            )
            self.scheduler.create_user_node(user_node)
        self.scheduler.node_assignment()
                
    def execute(self):
        self.scheduler.set_current_dataset(self.dataset_name)
        self.scheduler.set_sample_size(self.sample_size)
        if self.dataset_name == "none":
            self.scheduler.clear_all_users()
            return "Dataset cleared successfully"
        self.start_sample_data()
        if self.dataset_name == "taxiD_Replay":
            self.logger.info(
                f"TaxiD replay: created {len(self.scheduler.user_nodes)} users from "
                f"{len(self.scheduler.get_trajectories_px())} trajectories"
            )
        return f"Dataset set to {self.dataset_name} successfully"
