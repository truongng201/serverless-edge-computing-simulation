import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import numpy as np
import math
from datetime import datetime

try:
    from central_node.control_layer.prediction_module.tdrive_inference import (
        TDrivePredictorAdapter,
        get_mobility_prediction,
    )
except ImportError:
    TDrivePredictorAdapter = None  # type: ignore
    get_mobility_prediction = None

try:
    from shared.resource_layer.energy_model import EnergyModel, NodeType as EnergyNodeType, get_energy_model
except ImportError as e:
    logging.warning(f"Failed to import energy model: {e}")
    EnergyModel = None  # type: ignore
    EnergyNodeType = None  # type: ignore
    get_energy_model = None  # type: ignore

try:
    # Import the submodule directly to avoid dragging in psutil-dependent modules
    # (power_monitor, energy_model) when only the warm pool is needed.
    import importlib
    _wp_mod = importlib.import_module("shared.resource_layer.warm_pool")
    WarmPoolManager = _wp_mod.WarmPoolManager
except Exception as e:
    logging.warning(f"Failed to import warm pool manager: {e}")
    WarmPoolManager = None  # type: ignore

try:
    from shared.resource_layer.power_monitor import get_power_monitor, PowerMonitor
except ImportError as e:
    logging.warning(f"Failed to import power monitor: {e}")
    get_power_monitor = None  # type: ignore
    PowerMonitor = None  # type: ignore

from config import Config

from central_node.control_layer.models import EdgeNodeInfo, UserNodeInfo, NodeMetrics

LARGE_CAP = 1e12

class AssignmentAlgorithm(Enum):
    GREEDY = "greedy"
    RANDOM = "random"
    ROUND_ROBIN = "round robin"
    NEAREST = "nearest"
    CVX = "convex optimization"
    PREDICTIVE = "predictive"
    STICKY_GREEDY = "sticky greedy"
    GREEDY_KEEPALIVE = "greedy + keep-alive"
    PREDICTIVE_NO_WARM = "prediction without warm-state awareness"

class Scheduler:
    def __init__(self, assignment_algorithm: AssignmentAlgorithm = AssignmentAlgorithm.GREEDY):
        self.assignment_algorithm = assignment_algorithm
        self.edge_nodes: Dict[str, EdgeNodeInfo] = {}
        self.central_node = {
            "node_id": "central_node",
            "endpoint": "localhost:8000",
            "location": {"x": 2939, "y": 1835},  # Map center (5878x3670 / 2) - Beijing TaxiD bounds
            "coverage": 0 # default coverage
        }
        self.user_nodes: Dict[str, UserNodeInfo] = {}
        self.logger = logging.getLogger(__name__)
        self._round_robin_index = 0  # For round robin assignment tracking
        
        self.simulation = False
        self.assignment_matrix = {}
        self.dataset_metadata = {
            "dataset_name": "none",
            "sample_size": 0,
            "current_step_id": None,
            "trajectories_px": {}
        }

        self.warm_pool = WarmPoolManager() if WarmPoolManager else None
        # Per-node concurrent assignment counter (reset each timestep before assignment).
        self._assigned_concurrency: Dict[str, int] = {}
        # Per-timestep counters surfaced to metrics.
        self.timestep_rejections = 0
        self.timestep_evictions = 0

        self.history_max_points = getattr(Config, "TDRIVE_HISTORY_LENGTH", 20)
        self.predictor_adapter = None
        if TDrivePredictorAdapter and getattr(Config, "TDRIVE_ARTIFACT_DIR", None):
            try:
                self.predictor_adapter = TDrivePredictorAdapter(
                    Config.TDRIVE_ARTIFACT_DIR,
                    getattr(Config, "TDRIVE_CKPT_NAME", None),
                    getattr(Config, "TDRIVE_DEVICE", "cpu"),
                    temperature=getattr(Config, "TDRIVE_SOFTMAX_TEMPERATURE", 50.0),
                    max_radius=getattr(Config, "TDRIVE_MAX_RADIUS_M", None),
                )
                self.logger.info("T-Drive predictor adapter initialized successfully")
            except Exception as exc:
                self.logger.warning("Failed to initialize T-Drive predictor: %s", exc)
        elif self.assignment_algorithm == AssignmentAlgorithm.PREDICTIVE:
            self.logger.warning("Predictive scheduling requested but predictor is unavailable")


    def start_simulation(self):
        self.simulation = True
        
    def stop_simulation(self):
        self.simulation = False

    def get_edge_node(self, node_id: str) -> Optional[EdgeNodeInfo]:
        return self.edge_nodes.get(node_id)
    
    def update_edge_node(self, new_edge_node: EdgeNodeInfo):
        if new_edge_node.node_id not in self.edge_nodes:
            return
        self.edge_nodes[new_edge_node.node_id] = new_edge_node
        
    def get_central_node_info(self) -> Dict[str, Any]:
        return self.central_node
    
    def get_assignment_algorithm(self) -> str:
        return self.assignment_algorithm.value
    
    def get_all_assignment_algorithms(self) -> List[str]:
        return [algorithm.value for algorithm in AssignmentAlgorithm]

    def set_assignment_algorithm(self, assignment_algorithm: str):
        try:
            self.assignment_algorithm = AssignmentAlgorithm(assignment_algorithm)
        except ValueError:
            raise Exception(f"Invalid assignment algorithm: {assignment_algorithm}")
    
    def get_sample_size(self):
        return self.dataset_metadata.get("sample_size", 0)
    
    def set_sample_size(self, sample_size=100):
        self.dataset_metadata["sample_size"] = sample_size
        
    def get_current_dataset(self):
        return self.dataset_metadata.get("dataset_name", "none")
    
    def set_current_dataset(self, dataset_name):
        self.dataset_metadata["dataset_name"] = dataset_name
        
    def get_current_step_id(self):
        return self.dataset_metadata.get("current_step_id", None)
    
    def set_current_step_id(self, step_id=None):
        self.dataset_metadata["current_step_id"] = step_id
        
    def delete_all_user(self):
        self.user_nodes.clear()
    
    def delete_user_by_id(self, user_id):
        if user_id not in self.user_nodes:
            return
        del self.user_nodes[user_id]
        
    def get_user_by_id(self, user_id):
        if user_id not in self.user_nodes:
            return None
        return self.user_nodes[user_id]
    
    def get_trajectories_px(self):
        return self.dataset_metadata["trajectories_px"]
    
    def set_trajectories_px(self, trajectories_px):
        self.dataset_metadata["trajectories_px"] = trajectories_px
        
    def register_edge_node(self, node_info: EdgeNodeInfo):
        if node_info.node_id in self.edge_nodes:
            # Update specs/location on re-registration; preserve runtime metrics so
            # heartbeats and counters from a prior session are not wiped out.
            existing = self.edge_nodes[node_info.node_id]
            existing_metrics = getattr(existing, "metrics_info", None)
            if existing_metrics is not None and getattr(node_info, "metrics_info", None) is not None:
                # Heuristic: incoming controller seeds a "blank" NodeMetrics with all-zero
                # counters; if the existing one has activity, keep it.
                if getattr(existing_metrics, "total_requests", 0) > 0 or \
                   getattr(existing_metrics, "timestamp", 0) > 0:
                    node_info.metrics_info = existing_metrics
            self.edge_nodes[node_info.node_id] = node_info
            self.logger.info(f"Re-registered edge node (specs/location updated): {node_info.node_id}")
            return
        self.edge_nodes[node_info.node_id] = node_info
        self.logger.info(f"Registered edge node: {node_info.node_id}")

    def clear_edges(self):
        """Remove all registered edge nodes. Used by experiment runner between
        edge_range iterations to guarantee a clean fleet size."""
        n = len(self.edge_nodes)
        self.edge_nodes = {}
        self.logger.info(f"Cleared all {n} edge nodes")
        return n

    def unregister_edge_node(self, node_id: str):
        if node_id in self.edge_nodes:
            del self.edge_nodes[node_id]
            self.logger.info(f"Unregistered edge node: {node_id}")

    def update_node_metrics(self, node_id: str, new_metrics: NodeMetrics, system_info: Dict[str, Any], endpoint: str):
        if node_id in self.edge_nodes:
            self.edge_nodes[node_id].metrics_info = new_metrics
            self.edge_nodes[node_id].system_info = system_info
            self.edge_nodes[node_id].last_heartbeat = time.time()
        else:
            self.register_edge_node(EdgeNodeInfo(
                node_id=node_id,
                endpoint=endpoint,
                location={"x": 0.0, "y": 0.0},
                system_info=system_info,
                last_heartbeat=time.time(),
                metrics_info=new_metrics,
                coverage=300.0
            ))
        
    def update_user_node(self, user_id: str, new_location: Dict[str, float]) -> bool:
        if user_id not in self.user_nodes:
            return False
        user = self.user_nodes[user_id]
        user.location = new_location
        self._append_history_point(user, new_location)
        return True
    
    def update_user_node_with_features(self, user_id: str, point_data: Dict[str, float]) -> bool:
        """Update user with pre-computed features from trajectory data.
        
        This is more efficient than update_user_node() when features are already
        available from the exported trajectory file (with --include-features).
        
        Args:
            user_id: User identifier
            point_data: Dict containing x, y (pixels) and optionally pre-computed features
                       (v, a, delta_v, delta_heading, tod_sin, tod_cos, etc.)
        """
        if user_id not in self.user_nodes:
            return False
        
        user = self.user_nodes[user_id]
        user.location = {"x": point_data.get("x", 0.0), "y": point_data.get("y", 0.0)}
        
        # Check if features are pre-computed
        has_features = "v" in point_data
        
        if has_features:
            # Use pre-computed features directly
            self._append_history_point_with_features(user, point_data)
        else:
            # Fall back to computing features
            self._append_history_point(user, user.location)
        
        return True
    
    def _append_history_point_with_features(self, user_node: UserNodeInfo, point_data: Dict[str, float]) -> None:
        """Append a history point using pre-computed features from trajectory data.
        
        This uses features that were computed during prepare.py (from actual GPS data)
        which are more accurate than computing them from simulated pixel movements.
        """
        # Convert pixel coordinates to meters
        x_meters = float(point_data.get("x", 0.0)) * Config.DEFAULT_PIXEL_TO_METERS
        y_meters = float(point_data.get("y", 0.0)) * Config.DEFAULT_PIXEL_TO_METERS
        
        record = {
            "ts": time.time(),
            "x": x_meters,
            "y": y_meters,
            # Copy pre-computed features
            "v": float(point_data.get("v", 0.0)),
            "a": float(point_data.get("a", 0.0)),
            "delta_v": float(point_data.get("delta_v", 0.0)),
            "delta_heading": float(point_data.get("delta_heading", 0.0)),
            "tod_sin": float(point_data.get("tod_sin", 0.0)),
            "tod_cos": float(point_data.get("tod_cos", 0.0)),
            "dow_sin": float(point_data.get("dow_sin", 0.0)),
            "dow_cos": float(point_data.get("dow_cos", 0.0)),
            "rush_hour": float(point_data.get("rush_hour", 0.0)),
            "stop_flag": float(point_data.get("stop_flag", 0.0)),
            "dw_time": float(point_data.get("dw_time", 0.0)),
            # Optional graph-context features (present only if replay export included them)
            "node_degree": float(point_data.get("node_degree", 0.0)),
            "is_junction": float(point_data.get("is_junction", 0.0)),
        }
        
        user_node.history.append(record)
        if len(user_node.history) > self.history_max_points:
            user_node.history = user_node.history[-self.history_max_points:]
        
        self.user_nodes[user_node.user_id] = user_node

    def create_user_node(self, user_node: UserNodeInfo):
        self.user_nodes[user_node.user_id] = user_node
        self._append_history_point(user_node, user_node.location)

    def _append_history_point(self, user_node: UserNodeInfo, location: Dict[str, float]) -> None:
        """Append a history point with features computed in meters (consistent with model training).
        
        IMPORTANT: x,y are stored in METERS (converted from pixels) for consistency with 
        the prediction model which was trained on projected GPS coordinates in meters.
        """
        ts = time.time()
        # Convert pixel coordinates to meters for consistent coordinate system
        x_meters = float(location.get("x", 0.0)) * Config.DEFAULT_PIXEL_TO_METERS
        y_meters = float(location.get("y", 0.0)) * Config.DEFAULT_PIXEL_TO_METERS
        
        record = {
            "ts": ts,
            "x": x_meters,  # Now in meters
            "y": y_meters,  # Now in meters
        }
        prev = user_node.history[-1] if user_node.history else None
        if prev:
            dt = max(ts - prev.get("ts", ts), 1e-3)
            # Now dx, dy are already in meters (both current and previous are in meters)
            dx = record["x"] - prev.get("x", record["x"])
            dy = record["y"] - prev.get("y", record["y"])
            dist = math.hypot(dx, dy)
            v = dist / dt  # m/s
            prev_v = prev.get("v", 0.0)
            record["v"] = v
            record["delta_v"] = v - prev_v
            record["a"] = record["delta_v"] / dt  # m/s^2
            heading = math.atan2(dy, dx) if dist > 1e-6 else prev.get("heading", 0.0)
            record["heading"] = heading
            prev_heading = prev.get("heading", heading)
            delta_heading = ((heading - prev_heading) + math.pi) % (2 * math.pi) - math.pi
            record["delta_heading"] = delta_heading
            stop_flag = 1.0 if v < Config.PREDICTIVE_STOP_SPEED else 0.0
            record["stop_flag"] = stop_flag
            prev_dw = prev.get("dw_time", 0.0)
            record["dw_time"] = prev_dw + dt if stop_flag else 0.0
        else:
            record.update({
                "v": 0.0,
                "delta_v": 0.0,
                "a": 0.0,
                "heading": 0.0,
                "delta_heading": 0.0,
                "stop_flag": 1.0,  # First point is stationary
                "dw_time": 0.0,
            })
        dt_obj = datetime.fromtimestamp(ts)
        sec_day = dt_obj.hour * 3600 + dt_obj.minute * 60 + dt_obj.second
        record["tod_sin"] = math.sin(2 * math.pi * sec_day / 86400)
        record["tod_cos"] = math.cos(2 * math.pi * sec_day / 86400)
        dow = dt_obj.weekday()
        record["dow_sin"] = math.sin(2 * math.pi * dow / 7)
        record["dow_cos"] = math.cos(2 * math.pi * dow / 7)
        record["rush_hour"] = 1.0 if dt_obj.hour in range(7, 11) or dt_obj.hour in range(17, 21) else 0.0
        user_node.history.append(record)
        if len(user_node.history) > self.history_max_points:
            user_node.history = user_node.history[-self.history_max_points:]

        self.user_nodes[user_node.user_id] = user_node

    def _has_sufficient_history(self, history: List[Dict[str, float]]) -> bool:
        """Check if user has enough history points for reliable prediction.
        
        Rather than padding with synthetic data (which creates unrealistic patterns),
        we require at least `history_max_points` actual observations.
        """
        return len(history) >= self.history_max_points
    
    def _get_history_for_prediction(self, history: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """Get the most recent history_max_points for prediction."""
        if len(history) >= self.history_max_points:
            return history[-self.history_max_points:]
        return history  # Return as-is, caller should check sufficiency first
    
    def clear_all_users(self):
        self.user_nodes = {}

    def _classify_nodes(self):
        classified_nodes = {
            "healthy": set(),
            "warning": set(),
            "unhealthy": set()
        }

        for node in self.edge_nodes.values():
            if node.metrics_info.cpu_usage < Config.EDGE_NODE_WARNING_CPU_THRESHOLD and \
               node.metrics_info.memory_usage < Config.EDGE_NODE_WARNING_CPU_THRESHOLD:
                classified_nodes["healthy"].add(node.node_id)
            elif node.metrics_info.cpu_usage < Config.EDGE_NODE_UNHEALTHY_CPU_THRESHOLD and \
                 node.metrics_info.memory_usage < Config.EDGE_NODE_UNHEALTHY_MEMORY_THRESHOLD:
                classified_nodes["warning"].add(node.node_id)
            else:
                classified_nodes["unhealthy"].add(node.node_id)

        return classified_nodes
        
    def get_cluster_status(self) -> Dict[str, Any]:
        current_time = time.time()
        total_load = sum(node.metrics_info.cpu_usage for node in self.edge_nodes.values())
        average_load = total_load / len(self.edge_nodes) if self.edge_nodes else 0
        all_nodes_info = []
        
        classified_nodes = self._classify_nodes()

        for node in self.edge_nodes.values():
            last_seen = current_time - node.last_heartbeat
            node_status = "unidentified"
            if node.node_id in classified_nodes["healthy"]:
                node_status = "healthy"
            elif node.node_id in classified_nodes["warning"]:
                node_status = "warning"
            else:
                node_status = "unhealthy"
            node_info = {
                "node_id": node.node_id,
                "system_info": node.system_info,
                "location": node.location,
                "last_seen": last_seen,
                "endpoint": node.endpoint,
                "metrics": node.metrics_info,
                "coverage": node.coverage,
                "status": node_status
            }
            
            all_nodes_info.append(node_info)
            
        return {
            "total_nodes": len(self.edge_nodes),
            "average_load": average_load,
            "edge_nodes_info": all_nodes_info,
            "healthy_node_count": len(classified_nodes["healthy"]),
            "healthy_node_list": list(classified_nodes["healthy"]),
            "unhealthy_node_count": len(classified_nodes["unhealthy"]),
            "unhealthy_node_list": list(classified_nodes["unhealthy"]),
            "warning_node_count": len(classified_nodes["warning"]),
            "warning_node_list": list(classified_nodes["warning"]),
        }
    
    
    def _calculate_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        """Calculate distance between two locations in METERS.
        
        Locations are expected to be in pixels (UI coordinates), 
        and the result is converted to meters for physical calculations.
        """
        dx = (location1["x"] - location2["x"]) * Config.DEFAULT_PIXEL_TO_METERS
        dy = (location1["y"] - location2["y"]) * Config.DEFAULT_PIXEL_TO_METERS
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def _calculate_propagation_delay_deterministic(self, distance_meters: float) -> float:
        """Calculate deterministic 4G propagation delay in milliseconds.

        propagation_ms = RAN + fiber(distance) + hops(distance)

        where hops(distance) models urban backhaul aggregation routers:
        each AGG_SPACING_KM of distance crosses one more aggregation hop
        costing PER_HOP_LATENCY_MS. This makes distance a real signal
        (~22 ms spread between 1 and 69 km) without unphysical per-km
        coefficients.
        """
        distance_km = distance_meters / 1000.0
        ran = Config.NETWORK_RAN_LATENCY_MS
        fiber = distance_km * Config.NETWORK_FIBER_PER_KM_LATENCY_MS
        num_hops = math.ceil(distance_km / Config.NETWORK_AGG_SPACING_KM) if distance_km > 0 else 0
        hops = num_hops * Config.NETWORK_PER_HOP_LATENCY_MS
        return max(0.0, ran + fiber + hops)
    
    def _calculate_propagation_delay(self, distance_meters: float) -> float:
        """Calculate realistic network propagation delay in milliseconds.
        
        Uses a realistic network latency model instead of speed of light.
        The model includes:
        - Base latency: Radio access + core network baseline
        - Distance-based latency: Fiber/backhaul propagation
        
        Returns:
            Propagation delay in milliseconds
        """
        return self._calculate_propagation_delay_deterministic(distance_meters)
    
    def node_assignment(self) -> dict:
        # Per-timestep capacity counters must be reset before reassignment so that
        # the per-edge concurrency budget is enforced from a clean slate.
        self._reset_timestep_counters()
        if self.assignment_algorithm == AssignmentAlgorithm.GREEDY:
            return self._assign_users_greedy()
        elif self.assignment_algorithm == AssignmentAlgorithm.GREEDY_KEEPALIVE:
            return self._assign_users_greedy()
        elif self.assignment_algorithm == AssignmentAlgorithm.STICKY_GREEDY:
            return self._assign_users_sticky_greedy()
        elif self.assignment_algorithm == AssignmentAlgorithm.CVX:
            self._convex_optimization_assignment_all_users()
            return self.assignment_matrix
        elif self.assignment_algorithm in (
            AssignmentAlgorithm.PREDICTIVE,
            AssignmentAlgorithm.PREDICTIVE_NO_WARM,
        ):
            return self._predictive_assignment()
        elif self.assignment_algorithm == AssignmentAlgorithm.RANDOM:
            return self._assign_users_random()
        elif self.assignment_algorithm == AssignmentAlgorithm.ROUND_ROBIN:
            return self._assign_users_round_robin()
        elif self.assignment_algorithm == AssignmentAlgorithm.NEAREST:
            return self._assign_users_nearest()
        else:
            self.logger.error(f"Unknown assignment algorithm: {self.assignment_algorithm}")
            return self.assignment_matrix
            
    def _assign_users_greedy(self) -> dict:
        self.assignment_matrix = {}
        for user_id, user_node in self.user_nodes.items():
            candidate, _ = self._greedy_assignment(user_node.location)
            assigned_node_id, assigned_node_distance = self._apply_assignment_latency(user_node, candidate)
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        return self.assignment_matrix

    def _assign_users_random(self) -> dict:
        """Random baseline assignment: randomly assign each user to an available edge node.
        
        This serves as a baseline for comparison against greedy and predictive algorithms.
        It randomly selects an edge node (with resource constraints) for each user,
        demonstrating the value of intelligent assignment strategies.
        """
        self.assignment_matrix = {}
        edge_node_ids = list(self.edge_nodes.keys())

        for user_id, user_node in self.user_nodes.items():
            candidate, _ = self._random_assignment(user_node, edge_node_ids)
            assigned_node_id, assigned_node_distance = self._apply_assignment_latency(user_node, candidate)
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        return self.assignment_matrix

    def _random_assignment(self, user_node: UserNodeInfo, edge_node_ids: List[str]) -> Tuple[str, float]:
        """Randomly assign user to an edge node with resource constraints.
        
        Randomly selects from available edge nodes that can handle the user's resource demands.
        Falls back to central node if no edge nodes are available or have sufficient resources.
        
        Args:
            user_node: The user node to assign
            edge_node_ids: List of available edge node IDs
            
        Returns:
            Tuple of (assigned_node_id, distance_to_node)
        """
        if not edge_node_ids:
            # No edge nodes available, use central node
            distance = self._calculate_distance(user_node.location, self.central_node["location"])
            return self.central_node["node_id"], distance
        
        # Filter edge nodes that satisfy resource constraints
        available_nodes = [
            node_id for node_id in edge_node_ids
            if self._check_resource_constraints(user_node, node_id)
        ]
        
        if not available_nodes:
            # No edge nodes with sufficient resources, use central node
            distance = self._calculate_distance(user_node.location, self.central_node["location"])
            return self.central_node["node_id"], distance
        
        # Randomly select from available edge nodes
        selected_node_id = random.choice(available_nodes)
        selected_node = self.edge_nodes[selected_node_id]
        distance = self._calculate_distance(user_node.location, selected_node.location)
        
        return selected_node_id, distance

    def _assign_users_round_robin(self) -> dict:
        """Round Robin baseline: cyclically assign users to edge nodes.

        Distributes requests evenly across edge nodes in a rotating fashion,
        ignoring distance/latency considerations. Only respects resource constraints.

        Classical load-balancer RR is stateless: each arriving request goes to
        the next server. To avoid a batch-alignment artifact where user arrival
        order is identical every timestep (which makes user_i always land on
        edge_(i mod N) when N_users is divisible by N_edges), we shuffle the
        user iteration order with a step-seeded RNG. The shuffle is
        deterministic per step so runs remain reproducible.
        """
        self.assignment_matrix = {}
        edge_node_ids = sorted(self.edge_nodes.keys())

        current_step = self.get_current_step_id() or 0
        user_items = list(self.user_nodes.items())
        random.Random(current_step).shuffle(user_items)

        for user_id, user_node in user_items:
            candidate, _ = self._round_robin_assignment(user_node, edge_node_ids)
            assigned_node_id, assigned_node_distance = self._apply_assignment_latency(user_node, candidate)
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        return self.assignment_matrix

    def _round_robin_assignment(self, user_node: UserNodeInfo, edge_node_ids: List[str]) -> Tuple[str, float]:
        """Assign user using round-robin selection with resource constraints.
        
        Cycles through edge nodes in order, skipping nodes that don't have
        sufficient resources. Falls back to central node if no suitable edge found.
        """
        if not edge_node_ids:
            distance = self._calculate_distance(user_node.location, self.central_node["location"])
            return self.central_node["node_id"], distance
        
        # Try each edge node starting from current index
        attempts = 0
        while attempts < len(edge_node_ids):
            node_id = edge_node_ids[self._round_robin_index % len(edge_node_ids)]
            self._round_robin_index += 1
            attempts += 1
            
            if self._check_resource_constraints(user_node, node_id):
                node = self.edge_nodes[node_id]
                distance = self._calculate_distance(user_node.location, node.location)
                return node_id, distance
        
        # No suitable edge node found, use central node
        distance = self._calculate_distance(user_node.location, self.central_node["location"])
        return self.central_node["node_id"], distance

    def _assign_users_nearest(self) -> dict:
        """Nearest Node baseline: assign each user to the geographically closest edge node.
        
        Purely distance-based assignment without considering node load or health status.
        Only respects resource constraints. This is the primary baseline for comparison
        with predictive scheduling as both are location-aware.
        """
        self.assignment_matrix = {}

        for user_id, user_node in self.user_nodes.items():
            candidate, _ = self._nearest_assignment(user_node)
            assigned_node_id, assigned_node_distance = self._apply_assignment_latency(user_node, candidate)
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        return self.assignment_matrix

    def _nearest_assignment(self, user_node: UserNodeInfo) -> Tuple[str, float]:
        """Assign user to the nearest edge node with sufficient resources.
        
        Finds the closest edge node by Euclidean distance that can handle
        the user's resource demands. Falls back to central node if none available.
        """
        best_node = self.central_node["node_id"]
        min_distance = self._calculate_distance(user_node.location, self.central_node["location"])
        
        for node_id, node in self.edge_nodes.items():
            if not self._check_resource_constraints(user_node, node_id):
                continue
            distance = self._calculate_distance(user_node.location, node.location)
            if distance < min_distance:
                min_distance = distance
                best_node = node_id
        
        return best_node, min_distance

    def _predictive_assignment(self) -> dict:
        if getattr(Config, "PREDICTIVE_PREWARM_ONLY", False):
            return self._predictive_prewarm_only_assignment()

        if not self.predictor_adapter or not get_mobility_prediction:
            self.logger.warning("Predictor not available, falling back to greedy assignment")
            return self._assign_users_greedy()
        if not self.edge_nodes:
            self.logger.warning("No edge nodes registered; using greedy assignment")
            return self._assign_users_greedy()
        
        # Separate users into those with sufficient history (for prediction) 
        # and those without (for greedy fallback)
        user_states = []
        users_insufficient_history = []
        
        for user in self.user_nodes.values():
            if self._has_sufficient_history(user.history):
                # User has enough history for reliable prediction
                history = self._get_history_for_prediction(user.history)
                user_states.append({"user_id": user.user_id, "history": history})
            else:
                # User doesn't have enough history - will use greedy
                users_insufficient_history.append(user.user_id)
        
        # Log summary of user history status
        total_users = len(self.user_nodes)
        predictable_users = len(user_states)
        if users_insufficient_history:
            self.logger.info(
                f"Predictive assignment: {predictable_users}/{total_users} users have sufficient history, "
                f"{len(users_insufficient_history)} will use greedy fallback"
            )
        
        # If no users have sufficient history, use greedy for all
        if not user_states:
            self.logger.info("No users with sufficient history, using greedy assignment for all")
            return self._assign_users_greedy()
        
        # Convert cloudlet positions from pixels to meters (consistent with user history)
        cloudlet_records = [
            {
                "id": node_id, 
                "x": info.location["x"] * Config.DEFAULT_PIXEL_TO_METERS, 
                "y": info.location["y"] * Config.DEFAULT_PIXEL_TO_METERS
            }
            for node_id, info in self.edge_nodes.items()
        ]
        try:
            prob_map = get_mobility_prediction(user_states, cloudlet_records, self.predictor_adapter)
        except Exception as exc:
            self.logger.warning("Predictive inference failed: %s", exc)
            return self._assign_users_greedy()
        
        # Log prediction results summary
        predicted_count = len(prob_map)
        total_with_history = len(user_states)
        if predicted_count < total_with_history:
            self.logger.info(
                f"Prediction results: {predicted_count}/{total_with_history} users predicted successfully"
            )
        
        self.assignment_matrix = {}
        predictive_assignments = 0
        greedy_fallback_assignments = 0
        
        for user_id, user_node in self.user_nodes.items():
            probs = prob_map.get(user_id)
            if probs is None:
                candidate, _ = self._greedy_assignment(user_node.location)
                greedy_fallback_assignments += 1
            else:
                predictive_assignments += 1
                horizon_idx = -1
                if probs.ndim == 2 and probs.shape[1] > 0:
                    # Inference currently returns probabilities for horizons (1,3,5,10).
                    # Default to using horizon=5 (aligns better with the replay step and
                    # execution cadence), but clamp if the shape is unexpected.
                    desired_h = getattr(Config, "PREDICTIVE_TARGET_HORIZON_MIN", 5)
                    horizons = (1, 3, 5, 10)
                    if probs.shape[1] == len(horizons) and desired_h in horizons:
                        horizon_idx = horizons.index(desired_h)
                    else:
                        horizon_idx = min(max(int(desired_h) - 1, 0), probs.shape[1] - 1)
                order = np.argsort(probs[:, horizon_idx])[::-1]
                candidate = None
                for idx in order:
                    node_id = cloudlet_records[idx]["id"]
                    if self._check_resource_constraints(user_node, node_id):
                        candidate = node_id
                        break
                if candidate is None:
                    candidate = "central_node"
            assigned_node_id, assigned_node_distance = self._apply_assignment_latency(user_node, candidate)
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        
        # Log final assignment summary
        if predictive_assignments > 0 or greedy_fallback_assignments > 0:
            self.logger.info(
                f"Assignment complete: {predictive_assignments} predictive, "
                f"{greedy_fallback_assignments} greedy fallback"
            )
        
        return self.assignment_matrix

    def _apply_assignment_latency(self, user_node: UserNodeInfo, assigned_node_id: str) -> Tuple[str, float]:
        # Detect handoff BEFORE overwriting assigned_node_id
        prev_assigned = user_node.assigned_node_id
        handoff = prev_assigned is not None and prev_assigned != assigned_node_id
        self._account_assignment(assigned_node_id)

        if assigned_node_id == "central_node":
            location = self.central_node["location"]
        else:
            location = self.edge_nodes[assigned_node_id].location
        assigned_node_distance = self._calculate_distance(user_node.location, location)

        user_node.previous_node_id = prev_assigned
        user_node.assigned_node_id = assigned_node_id
        user_node.latency.distance = assigned_node_distance
        user_node.latency.propagation_delay = self._calculate_propagation_delay(assigned_node_distance)

        # Context switch cost: when a user is handed off to a different edge, its
        # session/DT state must be transferred. Modeled as state_size / bandwidth
        # (one-time, on the handoff step only). For serverless DT services this is
        # non-trivial and should be counted on top of any cold-start penalty.
        if handoff and user_node.bandwidth_demand and user_node.bandwidth_demand > 0:
            user_node.migration_cost = float(user_node.data_size_demand) / float(user_node.bandwidth_demand)
        else:
            user_node.migration_cost = 0.0

        user_node.latency.total_turnaround_time = (
            user_node.latency.propagation_delay
            + user_node.latency.transmission_delay
            + user_node.latency.computation_delay
            + user_node.migration_cost
        )
        return assigned_node_id, assigned_node_distance

    def _predictive_prewarm_only_assignment(self) -> dict:
        """Predictive mode that plans ahead but does not reassign immediately.

        - Keeps current assignment for serving requests "now".
        - On planning ticks, stores (planned_node_id, planned_step_id) per user based on horizon.
        - Switches assignment only when planned_step_id is reached.

        This mode is designed for experiments where wall-clock steps are slow (many users),
        so Docker warm TTL is not meaningful; the execution layer can model prewarm analytically.
        """
        if not self.predictor_adapter or not get_mobility_prediction:
            self.logger.warning("Predictor not available, falling back to greedy assignment")
            return self._assign_users_greedy()
        if not self.edge_nodes:
            self.logger.warning("No edge nodes registered; using greedy assignment")
            return self._assign_users_greedy()

        current_step = self.get_current_step_id() or 0
        lead_steps = int(getattr(Config, "PREDICTIVE_PREWARM_LEAD_STEPS", 5))
        exec_interval = int(getattr(Config, "PREDICTIVE_EXECUTE_INTERVAL_STEPS", 5))

        # Apply due switches first
        for user_node in self.user_nodes.values():
            if not user_node.planned_node_id or user_node.planned_step_id is None:
                continue
            if current_step < int(user_node.planned_step_id):
                continue
            # If we already passed the planned step, the prewarm signal is no longer needed.
            # Clear it to avoid repeatedly "re-applying" the same switch on later steps.
            if current_step > int(user_node.planned_step_id):
                user_node.planned_node_id = None
                user_node.planned_step_id = None
                continue
            candidate = user_node.planned_node_id
            if candidate != "central_node" and candidate not in self.edge_nodes:
                candidate = "central_node"
            if candidate != "central_node" and not self._check_resource_constraints(user_node, candidate):
                # Cannot switch to planned node; drop the plan and keep current assignment.
                user_node.planned_node_id = None
                user_node.planned_step_id = None
                continue
            # Apply the switch, but KEEP planned_node_id/step_id for this step so that
            # the execution layer can treat it as "prewarmed" on the switch step.
            # (get_all_users_controller.py checks planned_node_id/step_id when simulating cold/warm.)
            self._apply_assignment_latency(user_node, candidate)

        # Ensure an initial assignment exists (greedy) for any unassigned user
        for user_node in self.user_nodes.values():
            if user_node.assigned_node_id:
                continue
            assigned_node_id, _ = self._greedy_assignment(user_node.location)
            self._apply_assignment_latency(user_node, assigned_node_id)

        # Current assignment matrix reflects what serves requests "now"
        self.assignment_matrix = {
            user_id: (user.assigned_node_id, user.latency.distance)
            for user_id, user in self.user_nodes.items()
        }

        # Only plan on interval ticks (avoid expensive prediction every step)
        if exec_interval <= 0 or (current_step % exec_interval != 0):
            return self.assignment_matrix

        # Build prediction inputs for users with sufficient history
        user_states = []
        for user in self.user_nodes.values():
            if self._has_sufficient_history(user.history):
                history = self._get_history_for_prediction(user.history)
                user_states.append({"user_id": user.user_id, "history": history})

        if not user_states:
            return self.assignment_matrix

        cloudlet_records = [
            {
                "id": node_id,
                "x": info.location["x"] * Config.DEFAULT_PIXEL_TO_METERS,
                "y": info.location["y"] * Config.DEFAULT_PIXEL_TO_METERS,
            }
            for node_id, info in self.edge_nodes.items()
        ]

        try:
            prob_map = get_mobility_prediction(user_states, cloudlet_records, self.predictor_adapter)
        except Exception as exc:
            self.logger.warning("Predictive inference failed: %s", exc)
            return self.assignment_matrix

        desired_h = getattr(Config, "PREDICTIVE_TARGET_HORIZON_MIN", 5)
        horizons = (1, 3, 5, 10)
        for user_id, user_node in self.user_nodes.items():
            # If this user is switching *now* (planned_step_id == current_step),
            # keep the current plan fields intact for this step so the execution
            # layer can mark it as warm (prewarmed). We'll plan the next switch
            # on a later planning tick.
            if user_node.planned_step_id is not None and int(user_node.planned_step_id) == int(current_step):
                continue
            probs = prob_map.get(user_id)
            if probs is None or probs.ndim != 2 or probs.shape[1] <= 0:
                continue
            if probs.shape[1] == len(horizons) and desired_h in horizons:
                horizon_idx = horizons.index(desired_h)
            else:
                horizon_idx = min(max(int(desired_h) - 1, 0), probs.shape[1] - 1)

            order = np.argsort(probs[:, horizon_idx])[::-1]
            planned = None
            for idx in order:
                node_id = cloudlet_records[idx]["id"]
                if self._check_resource_constraints(user_node, node_id):
                    planned = node_id
                    break
            if planned is None:
                planned = "central_node"

            user_node.planned_node_id = planned
            user_node.planned_step_id = int(current_step) + int(lead_steps)

            # ACTUAL prewarm: consume a warm-pool slot at the planned node now.
            # If admission fails (no capacity), the prewarm is dropped and the
            # user will incur a real cold start at switch time — predictive does
            # not get a free pass.
            if self.warm_pool is not None and planned != "central_node":
                fn_id = self._function_id_for(user_node)
                admitted = self.warm_pool.admit_cold(planned, fn_id)
                if not admitted:
                    self.timestep_rejections += 1
                    user_node.planned_node_id = None
                    user_node.planned_step_id = None

        self.logger.info(
            "Predictive(prewarm-only): planned at step=%s -> switch at step+%s",
            current_step,
            lead_steps,
        )

        return self.assignment_matrix

    def _function_id_for(self, user_node: UserNodeInfo) -> str:
        if self.warm_pool is not None:
            return self.warm_pool.function_id_for_user(str(user_node.user_id))
        # Fallback if pool failed to import.
        return f"fn_user_{user_node.user_id}"

    def _check_resource_constraints(self, user_node: UserNodeInfo, cloudlet_id: str) -> bool:
        """Capacity check based on concurrent-user budget AND warm-pool capacity.

        Central node has a higher but finite budget (CENTRAL_MAX_CONCURRENT).
        Edge nodes are bounded by MAX_CONCURRENT_PER_EDGE for assigned users
        AND by MAX_WARM_PER_NODE for the warm function pool.
        """
        if cloudlet_id == "central_node":
            cap = int(getattr(Config, "CENTRAL_MAX_CONCURRENT", 256))
            return self._assigned_concurrency.get(cloudlet_id, 0) < cap

        if cloudlet_id not in self.edge_nodes:
            return False

        # Concurrent user budget per edge.
        edge_cap = int(getattr(Config, "MAX_CONCURRENT_PER_EDGE", 64))
        if self._assigned_concurrency.get(cloudlet_id, 0) >= edge_cap:
            return False

        # Memory headroom (only applies if metrics are present and credible).
        cloudlet = self.edge_nodes[cloudlet_id]
        try:
            if cloudlet.metrics_info and cloudlet.metrics_info.memory_total > 0:
                used_mem = cloudlet.metrics_info.memory_usage * cloudlet.metrics_info.memory_total / 100.0
                projected = (used_mem + user_node.memory_demand) / cloudlet.metrics_info.memory_total * 100.0
                if projected >= Config.EDGE_NODE_UNHEALTHY_MEMORY_THRESHOLD:
                    return False
        except Exception:
            pass

        return True

    def _reset_timestep_counters(self) -> None:
        self._assigned_concurrency = {}
        self.timestep_rejections = 0
        self.timestep_evictions = 0

    def _account_assignment(self, cloudlet_id: str) -> None:
        self._assigned_concurrency[cloudlet_id] = self._assigned_concurrency.get(cloudlet_id, 0) + 1
    
    
    def _greedy_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        '''
            RULE-BASED GREEDY ASSIGNMENT:
            1. Assign to the nearest healthy node within resource constraints.
            2. If no healthy node is available, assign to the nearest warning node within resource constraints.
            3. If no warning node is available, assign to the nearest unhealthy node within resource constraints.
            4. If no edge node is within resource constraints, assign to the central node.
        '''
        temp_user = UserNodeInfo(
            user_id="temp",
            assigned_node_id="",
            location=user_location,
            size=10,
            speed=5,
            last_executed=0,
            latency=None,
        )
        
        best_node = self.central_node["node_id"]
        min_distance = self._calculate_distance(user_location, self.central_node["location"])
        
        for node in self.edge_nodes.values():
            if not self._check_resource_constraints(temp_user, node.node_id):
                continue
            distance = self._calculate_distance(user_location, node.location)
            if distance < min_distance:
                min_distance = distance
                best_node = node.node_id

        return best_node, min_distance

   
    def calculate_turnaround_time_breakdown(self) -> Dict[str, float]:
        """Return total turnaround time split by container status (warm/cold/unknown).

        Adds per-user latency percentiles, average latency, warm-pool utilization,
        and rejected request count to support IEEE-quality metrics reporting.
        """
        total = 0.0
        warm_total = 0.0
        cold_total = 0.0
        unknown_total = 0.0
        warm_count = 0
        cold_count = 0
        unknown_count = 0
        per_user_latencies: List[float] = []

        for _, user_node in self.user_nodes.items():
            cloudlet_id = user_node.assigned_node_id
            if cloudlet_id == "central_node":
                distance = self._calculate_distance(user_node.location, self.central_node["location"])
            else:
                if not cloudlet_id or cloudlet_id not in self.edge_nodes:
                    continue
                cloudlet = self.edge_nodes[cloudlet_id]
                distance = self._calculate_distance(user_node.location, cloudlet.location)

            propagation_delay = self._calculate_propagation_delay(distance)
            transmission_delay = user_node.data_size_demand / user_node.bandwidth_demand
            computation_delay = getattr(getattr(user_node, "latency", None), "computation_delay", 0.0) or 0.0
            migration_cost = float(getattr(user_node, "migration_cost", 0.0) or 0.0)
            turnaround_time = propagation_delay + transmission_delay + computation_delay + migration_cost
            total += turnaround_time
            per_user_latencies.append(turnaround_time)

            status = str(getattr(getattr(user_node, "latency", None), "container_status", "unknown") or "unknown")
            if status == "warm":
                warm_total += turnaround_time
                warm_count += 1
            elif status == "cold":
                cold_total += turnaround_time
                cold_count += 1
            else:
                unknown_total += turnaround_time
                unknown_count += 1

        n = len(per_user_latencies)
        avg_latency = total / n if n > 0 else 0.0
        if n > 0:
            sorted_lat = sorted(per_user_latencies)
            def _pct(p: float) -> float:
                if n == 1:
                    return sorted_lat[0]
                idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
                return sorted_lat[idx]
            p50 = _pct(50.0)
            p95 = _pct(95.0)
            p99 = _pct(99.0)
        else:
            p50 = p95 = p99 = 0.0

        total_invocations = warm_count + cold_count + unknown_count
        warm_rate = (warm_count / total_invocations) if total_invocations > 0 else 0.0

        # Warm-pool utilization snapshot per node.
        pool_util = {}
        if getattr(self, "warm_pool", None) is not None:
            for node_id in self.edge_nodes.keys():
                pool_util[node_id] = self.warm_pool.utilization(node_id)
            pool_util["central_node"] = self.warm_pool.utilization("central_node")

        return {
            "total_turnaround_time": total,
            "total_turnaround_time_warm": warm_total,
            "total_turnaround_time_cold": cold_total,
            "total_turnaround_time_unknown": unknown_total,
            "warm_count": float(warm_count),
            "cold_count": float(cold_count),
            "unknown_count": float(unknown_count),
            # Quality-of-service metrics
            "avg_latency_ms": avg_latency,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "warm_rate": warm_rate,
            "rejected_count": float(getattr(self, "timestep_rejections", 0)),
            "pool_evictions": float(getattr(self, "timestep_evictions", 0)) if getattr(self, "warm_pool", None) is None
                else float(self.warm_pool.evictions),
            "pool_utilization_avg": (sum(pool_util.values()) / len(pool_util)) if pool_util else 0.0,
        }

    def calculate_total_turnaround_time(self) -> float:
        return float(self.calculate_turnaround_time_breakdown()["total_turnaround_time"])

    def calculate_energy_consumption(self, timestep_duration_s: float = 1.0, use_rapl: Optional[bool] = None) -> Dict[str, float]:
        """
        Calculate energy consumption for the current simulation state.
        
        Uses RAPL (Running Average Power Limit) for real power measurements when available,
        otherwise falls back to the estimated energy model.
        
        Energy formula:
            E_total = E_static + E_dynamic + E_network + E_cold_start
        
        Where:
            - E_static:     Idle/baseline power consumption of nodes
            - E_dynamic:    Workload-dependent compute power (CPU utilization based)
            - E_network:    Energy due to data transfer/offloading between nodes
            - E_cold_start: Container cold start overhead energy
        
        Args:
            timestep_duration_s: Duration of the timestep in seconds
            use_rapl: If True, use real RAPL measurements; if False, use estimation.
                     If None, uses Config.USE_RAPL setting.
            
        Returns:
            Dictionary with energy breakdown including source ('rapl' or 'estimate')
        """
        # Use config setting if not explicitly specified
        if use_rapl is None:
            use_rapl = getattr(Config, 'USE_RAPL', True)
        
        # Get turnaround breakdown for cold/warm counts
        breakdown = self.calculate_turnaround_time_breakdown()
        cold_count = int(breakdown.get("cold_count", 0))
        warm_count = int(breakdown.get("warm_count", 0))
        unknown_count = int(breakdown.get("unknown_count", 0))
        
        # Get node and user counts
        num_edge_nodes = len(self.edge_nodes) if self.edge_nodes else 1
        num_users = len(self.user_nodes) if self.user_nodes else 0
        
        # Calculate average CPU utilization across edge nodes
        avg_cpu_util = 0.0
        if self.edge_nodes:
            cpu_utils = []
            for node in self.edge_nodes.values():
                if node.metrics_info:
                    cpu_utils.append(node.metrics_info.cpu_usage)
            if cpu_utils:
                avg_cpu_util = sum(cpu_utils) / len(cpu_utils)
        
        # Get average data size and bandwidth from user nodes
        avg_data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
        avg_bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND * 1000  # Convert to bytes/s
        
        if self.user_nodes:
            data_sizes = [u.data_size_demand for u in self.user_nodes.values()]
            bandwidths = [u.bandwidth_demand for u in self.user_nodes.values()]
            if data_sizes:
                avg_data_size = sum(data_sizes) / len(data_sizes)
            if bandwidths:
                avg_bandwidth = (sum(bandwidths) / len(bandwidths)) * 1000
        
        # Try RAPL to get real power-per-node baseline
        rapl_power_per_node = None
        if use_rapl and get_power_monitor is not None:
            try:
                power_monitor = get_power_monitor()
                if power_monitor.use_rapl:
                    power_sample = power_monitor.get_current_power(sample_duration_s=0.1)
                    if power_sample and power_sample.get('source') == 'rapl':
                        # Use RAPL as a baseline for single-node power
                        # This represents real hardware power characteristics
                        rapl_power_per_node = power_sample['power_watts']
            except Exception as e:
                self.logger.warning(f"RAPL measurement failed: {e}")
        
        # Use estimation model (with optional RAPL power calibration)
        if get_energy_model is None or EnergyModel is None:
            self.logger.warning("Energy model not available")
            return {
                "static_energy_j": 0.0,
                "dynamic_energy_j": 0.0,
                "network_energy_j": 0.0,
                "cold_start_energy_j": 0.0,
                "total_energy_j": 0.0,
                "total_energy_wh": 0.0,
                "cold_start_count": 0,
                "warm_count": 0,
                "average_power_w": 0.0,
                "source": "unavailable"
            }
        
        energy_model = get_energy_model()
        
        # If RAPL gave us a power reading, use it to calibrate the model's power estimates
        # This makes the static/dynamic power based on real measurements
        if rapl_power_per_node is not None:
            # Override model's power profile with RAPL measurement
            # Assume RAPL measures idle+dynamic power at current CPU utilization
            # Scale by number of nodes (RAPL measures this single machine)
            energy_model.edge_power_profile.idle_power_w = rapl_power_per_node * 0.35
            energy_model.edge_power_profile.max_power_w = rapl_power_per_node
        
        # Calculate energy using the energy model (properly scales with nodes/users)
        energy_metrics = energy_model.estimate_timestep_energy(
            num_edge_nodes=num_edge_nodes,
            num_users=num_users,
            avg_edge_cpu_util=avg_cpu_util,
            avg_data_size_bytes=avg_data_size,
            avg_bandwidth_bytes_per_s=avg_bandwidth,
            cold_start_count=cold_count,
            warm_count=warm_count + unknown_count,  # Treat unknown as warm
            timestep_duration_s=timestep_duration_s
        )
        
        # Mark source based on whether RAPL was used for calibration
        if rapl_power_per_node is not None:
            energy_metrics["source"] = "rapl_calibrated"
            energy_metrics["rapl_power_w"] = round(rapl_power_per_node, 2)
        else:
            energy_metrics["source"] = "estimate"
        
        return energy_metrics
