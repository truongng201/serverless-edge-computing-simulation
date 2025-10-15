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
            for user_id, user_node in self.user_nodes.items():
                assigned_node_id, assigned_node_distance = self._greedy_assignment(user_node.location)
                user_node.assigned_node_id = assigned_node_id
                user_node.latency.distance = assigned_node_distance
                user_node.latency.propagation_delay = assigned_node_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
                total_turnaround_time = user_node.latency.propagation_delay + user_node.latency.transmission_delay + user_node.latency.computation_delay
                user_node.latency.total_turnaround_time = total_turnaround_time
                self.assignment_matrix[user_id] = (assigned_node_id, assigned_node_distance)
            return self.assignment_matrix
        elif self.assignment_algorithm == AssignmentAlgorithm.CVX:
            return self.assignment_matrix
        else:
            self.logger.error(f"Unknown assignment algorithm: {self.assignment_algorithm}")
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
        
        Objective: Minimize total turn around time for all users including the new user
        
        Constraints:
        - Assignment: each user assigned to exactly one cloudlet
        - Resource capacity: memory constraints
        """
        
        # Include existing users plus the new user
        existing_users = list(self.user_nodes.keys())
        users = existing_users + ["new_user"]
        cloudlets = list(self.edge_nodes.keys()) + ["central_node"]
        
        n_users = len(users)
        n_cloudlets = len(cloudlets)
        
        # Decision variables
        # a[i,j] = 1 if user i assigned to cloudlet j
        a = cp.Variable((n_users, n_cloudlets), boolean=True)
        
        # Parameters
        # Turnaround latency cost matrix T[i,j]
        T = np.zeros((n_users, n_cloudlets))
     
        # Resource demand matrices
        memory_demand = np.zeros(n_users)
        
        # Default values for new user
        new_user_memory_demand = Config.DEFAULT_USER_MEMORY_DEMAND
        new_user_bandwidth_demand = 10.0
        new_user_data_size_demand = 1024.0
        
        # Fill parameter matrices
        for i, user_id in enumerate(users):
            if user_id == "new_user":
                # New user parameters
                user_loc = user_location
                mem_dem = new_user_memory_demand
                bw_dem = new_user_bandwidth_demand
                data_size = new_user_data_size_demand
            else:
                # Existing user parameters
                user_node = self.user_nodes[user_id]
                user_loc = user_node.location
                mem_dem = user_node.memory_demand
                bw_dem = user_node.bandwidth_demand
                data_size = user_node.data_size_demand
                
            memory_demand[i] = mem_dem
            
            for j, cloudlet_id in enumerate(cloudlets):
                # Turnaround latency cost calculation
                if cloudlet_id == "central_node":
                    distance = self._calculate_distance(user_loc, self.central_node["location"])
                else:
                    cloudlet = self.edge_nodes[cloudlet_id]
                    distance = self._calculate_distance(user_loc, cloudlet.location)
                
                prop_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
                trans_delay = data_size / bw_dem
                
                # For existing users, use their computation delay if available
                if user_id != "new_user" and self.user_nodes[user_id].latency and self.user_nodes[user_id].latency.computation_delay:
                    comp_delay = self.user_nodes[user_id].latency.computation_delay
                else:
                    # Default computation delay estimate
                    comp_delay = 50.0  # milliseconds
                
                T[i, j] = prop_delay + trans_delay + comp_delay
    
        # Cloudlet capacities
        memory_capacity = np.zeros(n_cloudlets)
        
        # Fill cloudlet capacity parameters
        for j, cloudlet_id in enumerate(cloudlets):
            if cloudlet_id == "central_node":
                memory_capacity[j] = 999999  # Assume unlimited capacity for central node
            else:
                cloudlet = self.edge_nodes[cloudlet_id]
                # Calculate available memory (total - currently used)
                current_memory_used = (cloudlet.metrics_info.memory_usage / 100.0) * cloudlet.metrics_info.memory_total
                memory_capacity[j] = max(0, cloudlet.metrics_info.memory_total - current_memory_used)

        # Objective function: minimize total latency cost
        latency_cost = cp.sum(cp.multiply(T, a))
        objective = cp.Minimize(latency_cost)
        
        # Constraints
        constraints = []
        
        # Assignment constraint: each user assigned to exactly one cloudlet
        for i in range(n_users):
            constraints.append(cp.sum(a[i, :]) == 1)
        
        # Resource capacity constraints
        for j in range(n_cloudlets):
            # Memory constraint: sum of memory demands <= available memory capacity
            constraints.append(cp.sum(cp.multiply(memory_demand, a[:, j])) <= memory_capacity[j])
        
        # Solve the optimization problem
        problem = cp.Problem(objective, constraints)
        
        try:
            problem.solve(solver=cp.ECOS_BB, verbose=False)
        except Exception as e:
            self.logger.error(f"CVX solver error: {e}")
            return self._greedy_assignment(user_location)
        
        if problem.status == cp.OPTIMAL:
            # Store optimization results for metrics
            self._last_cvx_objective_value = problem.value
            self._last_cvx_latency_cost = latency_cost.value
            
            # Extract assignment for the new user (last user in list)
            new_user_idx = n_users - 1  # New user is at the end of the list
            assignment_vec = a.value[new_user_idx, :]
            assigned_cloudlet_idx = np.argmax(assignment_vec)
            assigned_cloudlet = cloudlets[assigned_cloudlet_idx]
            
            # Calculate actual distance for return value
            if assigned_cloudlet == "central_node":
                distance = self._calculate_distance(user_location, self.central_node["location"])
            else:
                cloudlet = self.edge_nodes[assigned_cloudlet]
                distance = self._calculate_distance(user_location, cloudlet.location)
                
            return assigned_cloudlet, distance
       
    def get_performance_summary_for_frontend(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics formatted for frontend display
        """
        # Calculate basic metrics
        total_turnaround_time = self.calculate_total_turnaround_time()
        total_users = len(self.user_nodes)
        
        # Calculate average resource utilization across edge nodes
        total_memory_util = 0
        total_cpu_util = 0
        active_nodes = 0
        
        for node in self.edge_nodes.values():
            if node.metrics_info:
                total_memory_util += node.metrics_info.memory_usage
                total_cpu_util += node.metrics_info.cpu_usage
                active_nodes += 1
        
        avg_memory_util = total_memory_util / max(1, active_nodes)
        avg_cpu_util = total_cpu_util / max(1, active_nodes)
        
        return {
            "algorithm": self.assignment_algorithm.value,
            "performance_metrics": {
                "total_cost": round(total_turnaround_time, 2),
                "total_turnaround_time": round(total_turnaround_time, 2),
                "total_migration_cost": 0.0,  # Placeholder - implement if migration is needed
                "total_cold_start_penalty": 0.0  # Placeholder - implement if cold starts are tracked
            },
            "resource_utilization": {
                "total_users": total_users,
                "avg_memory_utilization": round(avg_memory_util, 1),
                "avg_cpu_utilization": round(avg_cpu_util, 1),
                "avg_bandwidth_utilization": 0.0,  # Placeholder - implement if bandwidth tracking is needed
                "total_cold_starts": 0  # Placeholder - implement if cold starts are tracked
            },
        }
        
