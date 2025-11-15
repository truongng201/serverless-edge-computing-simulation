import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import time
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
            "location": {"x": 730, "y": 1070}, # default location
            "coverage": 0 # default coverage
        }
        self.user_nodes: Dict[str, UserNodeInfo] = {}
        self.logger = logging.getLogger(__name__)
        
        self.simulation = False
        self.assignment_matrix = {}
        self.current_dataset = None
        self.current_step_id = None

        self.history_max_points = getattr(Config, "TDRIVE_HISTORY_LENGTH", 20)
        self.predictor_adapter = None
        if TDrivePredictorAdapter and getattr(Config, "TDRIVE_ARTIFACT_DIR", None):
            try:
                self.predictor_adapter = TDrivePredictorAdapter(
                    Config.TDRIVE_ARTIFACT_DIR,
                    getattr(Config, "TDRIVE_CKPT_NAME", None),
                    getattr(Config, "TDRIVE_DEVICE", "cpu"),
                )
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
        self.user_nodes[user_id].location = new_location
        return True

    def create_user_node(self, user_node: UserNodeInfo):
        self.user_nodes[user_node.user_id] = user_node
        self._append_history_point(user_node, user_node.location)

    def _append_history_point(self, user_node: UserNodeInfo, location: Dict[str, float]) -> None:
        ts = time.time()
        record = {
            "ts": ts,
            "x": float(location.get("x", 0.0)),
            "y": float(location.get("y", 0.0)),
        }
        prev = user_node.history[-1] if user_node.history else None
        if prev:
            dt = max(ts - prev.get("ts", ts), 1e-3)
            dx = (record["x"] - prev.get("x", record["x"])) * Config.DEFAULT_PIXEL_TO_METERS
            dy = (record["y"] - prev.get("y", record["y"])) * Config.DEFAULT_PIXEL_TO_METERS
            dist = math.hypot(dx, dy)
            v = dist / dt
            prev_v = prev.get("v", 0.0)
            record["v"] = v
            record["delta_v"] = v - prev_v
            record["a"] = record["delta_v"] / dt
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
                "stop_flag": 0.0,
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
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5
    
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
            user_node.latency.propagation_delay = (
                assigned_node_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
            )
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
        user_states = []
        for user in self.user_nodes.values():
            if not user.history:
                continue
            history = user.history[-self.history_max_points :]
            user_states.append({"user_id": user.user_id, "history": history})
        if not user_states:
            return self._assign_users_greedy()
        cloudlet_records = [
            {"id": node_id, "x": info.location["x"], "y": info.location["y"]}
            for node_id, info in self.edge_nodes.items()
        ]
        try:
            prob_map = get_mobility_prediction(user_states, cloudlet_records, self.predictor_adapter)
        except Exception as exc:
            self.logger.warning("Predictive inference failed: %s", exc)
            return self._assign_users_greedy()
        self.assignment_matrix = {}
        for user_id, user_node in self.user_nodes.items():
            probs = prob_map.get(user_id)
            if probs is None:
                assigned_node_id, assigned_node_distance = self._greedy_assignment(user_node.location)
            else:
                horizon_idx = probs.shape[1] - 1 if probs.ndim == 2 else -1
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
            user_node.latency.propagation_delay = (
                assigned_node_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
            )
            total_turnaround_time = (
                user_node.latency.propagation_delay
                + user_node.latency.transmission_delay
                + user_node.latency.computation_delay
            )
            user_node.latency.total_turnaround_time = total_turnaround_time
            self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
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
            propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
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

                propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
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
                    user_node.latency.propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
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
                user_node.latency.propagation_delay = assigned_node_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
                total_turnaround_time = (
                    user_node.latency.propagation_delay +
                    getattr(user_node.latency, "transmission_delay", 0.0) +
                    getattr(user_node.latency, "computation_delay", 0.0)
                )
                user_node.latency.total_turnaround_time = total_turnaround_time
                self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)





