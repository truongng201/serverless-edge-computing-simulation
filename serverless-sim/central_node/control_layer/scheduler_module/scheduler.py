import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import time
from enum import Enum
import cvxpy as cp
import numpy as np
import random
from collections import defaultdict

from config import Config

from central_node.control_layer.models import EdgeNodeInfo, UserNodeInfo, NodeMetrics


class AssignmentAlgorithm(Enum):
    GREEDY = "greedy"
    CVX = "convex optimization"

class Scheduler:
    def __init__(self, assignment_algorithm: AssignmentAlgorithm = AssignmentAlgorithm.CVX):
        self.assignment_algorithm = assignment_algorithm
        self.edge_nodes: Dict[str, EdgeNodeInfo] = {}
        self.central_node = {
            "node_id": "central_node",
            "endpoint": "localhost:8000",
            "location": {"x": 600, "y": 400}, # default location
            "coverage": 0 # default coverage
        }
        self.user_nodes: Dict[str, UserNodeInfo] = {}
        self.logger = logging.getLogger(__name__)
        
        self.simulation = False
        self.current_dataset = None
        self.current_step_id = None

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
        assigned_node_id, assigned_node_distance = self.node_assignment(new_location)
        self.user_nodes[user_id].assigned_node_id = assigned_node_id
        self.user_nodes[user_id].latency.distance = assigned_node_distance
        
        return True

    def create_user_node(self, user_node: UserNodeInfo):
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
    
    def node_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        if self.assignment_algorithm == AssignmentAlgorithm.GREEDY:
            return self._greedy_assignment(user_location)
        elif self.assignment_algorithm == AssignmentAlgorithm.CVX:
            return self._greedy_assignment(user_location)
        else:
            raise Exception(f"Unknown assignment algorithm: {self.assignment_algorithm}")

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
                cloudlet = self.edge_nodes[cloudlet_id]
                distance = self._calculate_distance(user_node.location, cloudlet.location)
            propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
            transmission_delay = user_node.data_size_demand / user_node.bandwidth_demand
            computation_delay = user_node.latency.computation_delay if user_node.latency.computation_delay else 0
            turnaround_time = propagation_delay + transmission_delay + computation_delay
            total_turnaround_time += turnaround_time
        
        return total_turnaround_time


    def _convex_optimization_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        """
        CVX Convex Optimization Assignment implementing the mathematical formulation:
        
        Variables:
        - a_ij^t: binary assignment of user i to cloudlet j at time t
        - b_ijk^t: binary migration from cloudlet j to k for user i at time t  
        - cs_j^t: number of cold starts on cloudlet j at time t
        
        Objective: Minimize total latency + migration cost + cold start penalty
        
        Constraints:
        - Assignment: each user assigned to exactly one cloudlet
        - Coverage: users only assigned to cloudlets in range
        - Resource capacity: memory, CPU, bandwidth limits
        - Migration flow consistency
        """
        
        users = list(self.user_nodes.keys())
        cloudlets = list(self.edge_nodes.keys()) + ["central_node"]
        
        n_users = len(users)
        n_cloudlets = len(cloudlets)
        
        # Decision variables
        # a[i,j] = 1 if user i assigned to cloudlet j
        a = cp.Variable((n_users, n_cloudlets), boolean=True)
        
        # cs[j] = number of cold starts on cloudlet j
        cs = cp.Variable(n_cloudlets, integer=True)
        
        # Parameters
        # Turnaround latency cost matrix T[i,j]
        T = np.zeros((n_users, n_cloudlets))
        
        # Coverage matrix cov[i,j]
        cov = np.zeros((n_users, n_cloudlets))
        
        # Resource demand matrices
        memory_demand = np.zeros(n_users)
        cpu_demand = np.zeros(n_users) 
        bandwidth_demand = np.zeros(n_users)
        
        # Cloudlet capacities
        memory_capacity = np.zeros(n_cloudlets)
        cpu_capacity = np.zeros(n_cloudlets)
        bandwidth_capacity = np.zeros(n_cloudlets)
        warm_containers = np.zeros(n_cloudlets)
        cold_penalty = np.zeros(n_cloudlets)
        
        # Fill parameter matrices
        for i, user_id in enumerate(users):
            if user_id == "temp_user":
                # Use provided location for new user
                user_loc = user_location
                mem_dem = 128.0
                cpu_dem = 1.0
                bw_dem = 10.0
            else:
                user_node = self.user_nodes[user_id]
                user_loc = user_node.location
                mem_dem = user_node.memory_demand
                cpu_dem = user_node.cpu_demand
                bw_dem = user_node.bandwidth_demand
                
            memory_demand[i] = mem_dem
            cpu_demand[i] = cpu_dem
            bandwidth_demand[i] = bw_dem
            
            for j, cloudlet_id in enumerate(cloudlets):
                # Turnaround latency cost
                if cloudlet_id == "central_node":
                    T[i, j] = 100.0
                else:
                    cloudlet = self.edge_nodes[cloudlet_id]
                    distance = self._calculate_distance(user_loc, cloudlet.location)
                    prop_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
                    trans_delay = 1024.0 / (bw_dem * 1024 * 1024)  # Convert Mbps to bytes/ms
                    comp_delay = cpu_dem * 10
                    T[i, j] = prop_delay + trans_delay + comp_delay
        
        # Fill cloudlet capacity parameters
        for j, cloudlet_id in enumerate(cloudlets):
            if cloudlet_id == "central_node":
                memory_capacity[j] = 999999  # Unlimited
                cpu_capacity[j] = 999999
                bandwidth_capacity[j] = 999999
                warm_containers[j] = 999999
                cold_penalty[j] = 0
            else:
                cloudlet = self.edge_nodes[cloudlet_id]
                memory_capacity[j] = cloudlet.memory_capacity
                cpu_capacity[j] = cloudlet.cpu_capacity
                bandwidth_capacity[j] = cloudlet.bandwidth_capacity
                warm_containers[j] = cloudlet.warm_containers
                cold_penalty[j] = 50.0  # Cold start penalty
        
        # Objective function: minimize total cost
        latency_cost = cp.sum(cp.multiply(T, a))
        cold_start_cost = cp.sum(cp.multiply(cold_penalty, cs))
        objective = cp.Minimize(latency_cost + cold_start_cost)
        
        # Constraints
        constraints = []
        
        # Assignment constraint: each user to exactly one cloudlet
        for i in range(n_users):
            constraints.append(cp.sum(a[i, :]) == 1)
        
   
        
        # Resource capacity constraints
        for j in range(n_cloudlets):
            # Memory constraint
            constraints.append(cp.sum(cp.multiply(memory_demand, a[:, j])) <= memory_capacity[j])
            # CPU constraint  
            constraints.append(cp.sum(cp.multiply(cpu_demand, a[:, j])) <= cpu_capacity[j])
            # Bandwidth constraint
            constraints.append(cp.sum(cp.multiply(bandwidth_demand, a[:, j])) <= bandwidth_capacity[j])
        
        # Cold start constraints
        for j in range(n_cloudlets):
            constraints.append(cs[j] >= cp.sum(a[:, j]) - warm_containers[j])
            constraints.append(cs[j] >= 0)
            constraints.append(cs[j] <= cp.sum(a[:, j]))
        
        # Solve the optimization problem
        try:
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS_BB, verbose=False)
            
            if problem.status == cp.OPTIMAL:
                # Store optimization results for metrics
                self._last_cvx_objective_value = problem.value
                self._last_cvx_latency_cost = latency_cost.value
                self._last_cvx_cold_start_cost = cold_start_cost.value
                
                # Extract assignment for the new user (last user in list)
                new_user_idx = n_users - 1
                assignment_vec = a.value[new_user_idx, :]
                assigned_cloudlet_idx = np.argmax(assignment_vec)
                assigned_cloudlet = cloudlets[assigned_cloudlet_idx]
                
                # Calculate distance
                if assigned_cloudlet == "central_node":
                    distance = 1000.0
                else:
                    cloudlet = self.edge_nodes[assigned_cloudlet]
                    distance = self._calculate_distance(user_location, cloudlet.location)
                    
                return assigned_cloudlet, distance
            else:
                self.logger.warning(f"CVX optimization failed with status: {problem.status}")
                # Fallback to greedy
                return self._greedy_assignment(user_location)
                
        except Exception as e:
            self.logger.error(f"CVX optimization error: {e}")
            # Fallback to greedy
            return self._greedy_assignment(user_location)
        