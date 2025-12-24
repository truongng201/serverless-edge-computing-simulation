import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import cvxpy as cp
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


from config import Config

from central_node.control_layer.models import EdgeNodeInfo, UserNodeInfo, NodeMetrics

LARGE_CAP = 1e12

class AssignmentAlgorithm(Enum):
    GREEDY = "greedy"
    CVX = "convex optimization"
    PREDICTIVE = "predictive"

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
        
        self.simulation = False
        self.assignment_matrix = {}
        self.dataset_metadata = {
            "dataset_name": "none",
            "sample_size": 0,
            "current_step_id": None,
            "trajectories_px": {}
        }

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
            self.logger.info(f"Edge node {node_info.node_id} is already registered")
            return
        self.edge_nodes[node_info.node_id] = node_info
        self.logger.info(f"Registered edge node: {node_info.node_id}")
        
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
        """Calculate deterministic network propagation delay.
        
        Used for optimization algorithms (CVX) that need consistent values.
        
        Returns:
            Propagation delay in milliseconds
        """
        distance_km = distance_meters / 1000.0
        base_latency = Config.NETWORK_BASE_LATENCY_MS
        distance_latency = distance_km * Config.NETWORK_PER_KM_LATENCY_MS
        
        return max(0.0, base_latency + distance_latency)
    
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
        if self.assignment_algorithm == AssignmentAlgorithm.GREEDY:
            return self._assign_users_greedy()
        elif self.assignment_algorithm == AssignmentAlgorithm.CVX:
            self._convex_optimization_assignment_all_users()
            return self.assignment_matrix
        elif self.assignment_algorithm == AssignmentAlgorithm.PREDICTIVE:
            return self._predictive_assignment()
        else:
            self.logger.error(f"Unknown assignment algorithm: {self.assignment_algorithm}")
            return self.assignment_matrix
            
    def _assign_users_greedy(self) -> dict:
        self.assignment_matrix = {}
        for user_id, user_node in self.user_nodes.items():
            assigned_node_id, assigned_node_distance = self._greedy_assignment(user_node.location)
            user_node.assigned_node_id = assigned_node_id
            user_node.latency.distance = assigned_node_distance
            user_node.latency.propagation_delay = self._calculate_propagation_delay(assigned_node_distance)
            total_turnaround_time = (
                user_node.latency.propagation_delay
                + user_node.latency.transmission_delay
                + user_node.latency.computation_delay
            )
            user_node.latency.total_turnaround_time = total_turnaround_time
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        return self.assignment_matrix

    def _predictive_assignment(self) -> dict:
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
                assigned_node_id, assigned_node_distance = self._greedy_assignment(user_node.location)
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
                assigned_node_id = None
                for idx in order:
                    node_id = cloudlet_records[idx]["id"]
                    if self._check_resource_constraints(user_node, node_id):
                        assigned_node_id = node_id
                        break
                if assigned_node_id is None:
                    assigned_node_id = "central_node"
                if assigned_node_id == "central_node":
                    location = self.central_node["location"]
                else:
                    location = self.edge_nodes[assigned_node_id].location
                assigned_node_distance = self._calculate_distance(user_node.location, location)
            user_node.assigned_node_id = assigned_node_id
            user_node.latency.distance = assigned_node_distance
            user_node.latency.propagation_delay = self._calculate_propagation_delay(assigned_node_distance)
            total_turnaround_time = (
                user_node.latency.propagation_delay
                + user_node.latency.transmission_delay
                + user_node.latency.computation_delay
            )
            user_node.latency.total_turnaround_time = total_turnaround_time
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
        
        # Log final assignment summary
        if predictive_assignments > 0 or greedy_fallback_assignments > 0:
            self.logger.info(
                f"Assignment complete: {predictive_assignments} predictive, "
                f"{greedy_fallback_assignments} greedy fallback"
            )
        
        return self.assignment_matrix

    def _check_resource_constraints(self, user_node: UserNodeInfo, cloudlet_id: str) -> bool:
        if cloudlet_id == "central_node":
            return True  # Assume central node has unlimited capacity
            
        if cloudlet_id not in self.edge_nodes:
            return False
        
        cloudlet = self.edge_nodes[cloudlet_id]
        if cloudlet.metrics_info.cpu_usage < Config.EDGE_NODE_UNHEALTHY_CPU_THRESHOLD:
            x = (cloudlet.metrics_info.memory_usage * cloudlet.metrics_info.memory_total / 100 + user_node.memory_demand) / cloudlet.metrics_info.memory_total * 100
            if x < Config.EDGE_NODE_UNHEALTHY_MEMORY_THRESHOLD:
                return True
        return False  
    
    
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

   
    def calculate_total_turnaround_time(self) -> Dict[str, float]:
        total_turnaround_time = 0.0
        
        for _, user_node in self.user_nodes.items():
            # Turnaround latency cost
            distance = 0
            turnaround_time = 0
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
            computation_delay = user_node.latency.computation_delay if user_node.latency.computation_delay else 0
            turnaround_time = propagation_delay + transmission_delay + computation_delay
            total_turnaround_time += turnaround_time
        
        return total_turnaround_time


    def _convex_optimization_assignment_all_users(self):
        if not self.user_nodes:
            return
            
        users = list(self.user_nodes.keys())
        # Include both edge nodes and central node
        edge_cloudlets = list(self.edge_nodes.keys())
        cloudlets = edge_cloudlets + ["central_node"]
        
        n_users = len(users)
        n_cloudlets = len(cloudlets)
        if n_users == 0 or n_cloudlets == 0:
            return

        # Variables: relaxed continuous assignment
        a = cp.Variable((n_users, n_cloudlets))
        T = np.zeros((n_users, n_cloudlets))
        memory_demand = np.zeros(n_users)
        
        # Calculate turnaround times and memory demands
        for i, user_id in enumerate(users):
            user_node = self.user_nodes[user_id]
            user_loc = user_node.location
            memory_demand[i] = user_node.memory_demand
            
            for j, cloudlet_id in enumerate(cloudlets):
                if cloudlet_id == "central_node":
                    distance = self._calculate_distance(user_loc, self.central_node["location"])
                else:
                    distance = self._calculate_distance(user_loc, self.edge_nodes[cloudlet_id].location)

                # For CVX optimization, use deterministic propagation delay (no jitter)
                # to ensure consistent optimization results
                propagation_delay = self._calculate_propagation_delay_deterministic(distance)
                computation_delay = getattr(user_node.latency, "computation_delay", 0.0)
                transmission_delay = getattr(user_node.latency, "transmission_delay", 0.0)
                T[i, j] = propagation_delay + transmission_delay + computation_delay

        # Normalize turnaround times to improve numerical stability
        T_max = np.max(T)
        if T_max > 0:
            T /= T_max

        # Set memory capacities
        memory_capacity = np.zeros(n_cloudlets)
        for j, cloudlet_id in enumerate(cloudlets):
            if cloudlet_id == "central_node":
                # Central node has unlimited capacity
                memory_capacity[j] = LARGE_CAP
            else:
                # Edge node capacity calculation
                edge_node = self.edge_nodes[cloudlet_id]
                used_memory = (edge_node.metrics_info.memory_usage / 100.0) * edge_node.metrics_info.memory_total
                available_memory = max(0, edge_node.metrics_info.memory_total - used_memory)
                memory_capacity[j] = available_memory

        # Objective: minimize total weighted turnaround time
        # Add penalty for using central node to prefer edge nodes when possible
        penalty_weight = np.ones((n_users, n_cloudlets))
        central_node_idx = cloudlets.index("central_node")
        penalty_weight[:, central_node_idx] = 1.2  # Slight penalty for central node usage
        
        weighted_T = np.multiply(T, penalty_weight)
        objective = cp.Minimize(cp.sum(cp.multiply(weighted_T, a)))

        constraints = []

        # Each user must be assigned to exactly one cloudlet
        for i in range(n_users):
            constraints.append(cp.sum(a[i, :]) == 1)

        # Memory capacity constraints for all cloudlets
        for j in range(n_cloudlets):
            constraints.append(cp.sum(cp.multiply(memory_demand, a[:, j])) <= memory_capacity[j])

        # Assignment variables must be between 0 and 1
        constraints += [a >= 0, a <= 1]

        problem = cp.Problem(objective, constraints)

        try:
            # Try multiple solvers for better success rate
            solvers_to_try = [cp.ECOS, cp.SCS, cp.CLARABEL] if hasattr(cp, 'CLARABEL') else [cp.ECOS, cp.SCS]
            
            solved = False
            for solver in solvers_to_try:
                try:
                    if solver == cp.SCS:
                        problem.solve(solver=solver, verbose=False, max_iters=5000, eps=1e-4)
                    else:
                        problem.solve(solver=solver, verbose=False)
                    
                    if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                        solved = True
                        break
                except:
                    continue
            
            print(f"[CVX] Status: {problem.status}, Objective: {problem.value}")

            if solved and a.value is not None:
                assign_vals = a.value
                
                # Assign users to cloudlets based on optimization result
                for i, user_id in enumerate(users):
                    # Find the cloudlet with highest assignment probability
                    assigned_idx = int(np.argmax(assign_vals[i, :]))
                    assigned_cloudlet = cloudlets[assigned_idx]
                    
                    # Verify the assignment is valid (resource constraints)
                    user_node = self.user_nodes[user_id]
                    if not self._check_resource_constraints(user_node, assigned_cloudlet):
                        # If assignment violates constraints, fall back to central node
                        assigned_cloudlet = "central_node"
                        assigned_idx = central_node_idx
                    
                    # Calculate distance and latency
                    if assigned_cloudlet == "central_node":
                        distance = self._calculate_distance(user_node.location, self.central_node["location"])
                    else:
                        distance = self._calculate_distance(user_node.location, self.edge_nodes[assigned_cloudlet].location)

                    # Update user node assignment and latency information
                    user_node.assigned_node_id = assigned_cloudlet
                    user_node.latency.distance = distance
                    user_node.latency.propagation_delay = self._calculate_propagation_delay(distance)
                    total_turnaround_time = (
                        user_node.latency.propagation_delay +
                        getattr(user_node.latency, "transmission_delay", 0.0) +
                        getattr(user_node.latency, "computation_delay", 0.0)
                    )
                    user_node.latency.total_turnaround_time = total_turnaround_time
                    self.assignment_matrix[user_id] = (assigned_cloudlet, distance)
                
                print(f"[CVX] Optimization successful, total normalized cost: {problem.value:.4f}")

            else:
                raise Exception(f"CVX failed with status {problem.status}")

        except Exception as e:
            self.logger.error(f"Error in CVX optimization: {e}. Falling back to greedy assignment.")
            # Fallback to greedy assignment
            for user_id, user_node in self.user_nodes.items():
                assigned_node_id, assigned_node_distance = self._greedy_assignment(user_node.location)
                user_node.assigned_node_id = assigned_node_id
                user_node.latency.distance = assigned_node_distance
                user_node.latency.propagation_delay = self._calculate_propagation_delay(assigned_node_distance)
                total_turnaround_time = (
                    user_node.latency.propagation_delay +
                    getattr(user_node.latency, "transmission_delay", 0.0) +
                    getattr(user_node.latency, "computation_delay", 0.0)
                )
                user_node.latency.total_turnaround_time = total_turnaround_time
                self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
