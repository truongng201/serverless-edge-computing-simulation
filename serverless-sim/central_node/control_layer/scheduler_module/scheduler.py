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
            raise Exception(f"Node {node_info.node_id} is already registered")
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
    
    def node_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        if self.assignment_algorithm == AssignmentAlgorithm.GREEDY:
            return self._greedy_assignment(user_location)
        elif self.assignment_algorithm == AssignmentAlgorithm.CVX:
            return self._convex_optimization_assignment(user_location)
        else:
            raise Exception(f"Unknown assignment algorithm: {self.assignment_algorithm}")

    def node_assignment_with_metrics(self, user_location: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        """
        Enhanced assignment that also returns performance metrics
        Returns: (assigned_node, distance, objective_metrics)
        """
        # Store current state
        old_objective = self.calculate_total_objective_function()
        
        # Perform assignment
        assigned_node, distance = self.node_assignment(user_location)
        
        # Calculate new objective (this would be after actually creating the user)
        # For now, we estimate the impact
        estimated_metrics = {
            "estimated_turnaround_time": self._calculate_turnaround_latency_for_location(user_location, assigned_node),
            "estimated_migration_cost": 0.0,  # New user, no migration
            "estimated_cold_start_penalty": self._estimate_cold_start_penalty(assigned_node),
            "algorithm_used": self.assignment_algorithm.value,
            "current_total_cost": old_objective["total_cost"]
        }
        
        return assigned_node, distance, estimated_metrics

    def _calculate_turnaround_latency_for_location(self, user_location: Dict[str, float], cloudlet_id: str) -> float:
        """Calculate turnaround latency for a location without creating a user node"""
        if cloudlet_id == "central_node":
            return 100.0
        else:
            cloudlet = self.edge_nodes[cloudlet_id]
            distance = self._calculate_distance(user_location, cloudlet.location)
            propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
            transmission_delay = 1024.0 / (10.0 * 1024 * 1024)  # Default values
            computation_delay = 1.0 * 10  # Default CPU demand
            return propagation_delay + transmission_delay + computation_delay

    def _estimate_cold_start_penalty(self, cloudlet_id: str) -> float:
        """Estimate cold start penalty if one more user is added"""
        if cloudlet_id == "central_node":
            return 0.0
            
        current_users = sum(1 for u in self.user_nodes.values() if u.assigned_node_id == cloudlet_id)
        return self._calculate_cold_start_penalty(cloudlet_id, current_users + 1)

    def _calculate_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5

    def _check_coverage(self, user_location: Dict[str, float], cloudlet_id: str) -> bool:
        """Check if user is within coverage range of cloudlet (cov_ij^t)"""
        if cloudlet_id == "central_node":
            return True
            
        if cloudlet_id not in self.edge_nodes:
            return False
            
        cloudlet = self.edge_nodes[cloudlet_id]
        distance = self._calculate_distance(user_location, cloudlet.location)
        return distance <= cloudlet.coverage

    def _check_resource_constraints(self, user_node: UserNodeInfo, cloudlet_id: str) -> bool:
        """Check if cloudlet has sufficient resources for user"""
        if cloudlet_id == "central_node":
            return True  # Assume central node has unlimited capacity
            
        if cloudlet_id not in self.edge_nodes:
            return False
            
        cloudlet = self.edge_nodes[cloudlet_id]
        
        # Calculate current resource usage
        current_memory = sum(u.memory_demand for u in self.user_nodes.values() 
                           if u.assigned_node_id == cloudlet_id)
        current_cpu = sum(u.cpu_demand for u in self.user_nodes.values() 
                         if u.assigned_node_id == cloudlet_id)
        current_bandwidth = sum(u.bandwidth_demand for u in self.user_nodes.values() 
                              if u.assigned_node_id == cloudlet_id)
        
        # Check constraints
        memory_ok = (current_memory + user_node.memory_demand) <= cloudlet.memory_capacity
        cpu_ok = (current_cpu + user_node.cpu_demand) <= cloudlet.cpu_capacity
        bandwidth_ok = (current_bandwidth + user_node.bandwidth_demand) <= cloudlet.bandwidth_capacity
        
        return memory_ok and cpu_ok and bandwidth_ok

    def _calculate_turnaround_latency(self, user_node: UserNodeInfo, cloudlet_id: str) -> float:
        """Calculate T_ij^t - turnaround latency cost"""
        if cloudlet_id == "central_node":
            base_latency = 100.0  # Higher latency for central processing
        else:
            cloudlet = self.edge_nodes[cloudlet_id]
            distance = self._calculate_distance(user_node.location, cloudlet.location)
            propagation_delay = distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000
            transmission_delay = user_node.data_size_demand / (user_node.bandwidth_demand * 1024 * 1024)  # Convert Mbps to bytes/ms
            computation_delay = user_node.cpu_demand * 10  # Simplified computation model
            base_latency = propagation_delay + transmission_delay + computation_delay
            
        return base_latency

    def _calculate_migration_cost(self, user_id: str, from_cloudlet: str, to_cloudlet: str) -> float:
        """Calculate migration cost between cloudlets"""
        if from_cloudlet == to_cloudlet:
            return 0.0
            
        user_node = self.user_nodes.get(user_id)
        if not user_node:
            return 0.0
            
        # Migration cost includes data transfer cost
        migration_data_size = user_node.data_size_demand
        if from_cloudlet == "central_node" or to_cloudlet == "central_node":
            # Higher cost for central-edge migration
            return migration_data_size * 0.1
        else:
            # Edge-to-edge migration
            return migration_data_size * 0.05

    def _calculate_cold_start_penalty(self, cloudlet_id: str, num_users: int) -> float:
        """Calculate cold start penalty for cloudlet"""
        if cloudlet_id == "central_node":
            return 0.0  # No cold start penalty for central node
            
        cloudlet = self.edge_nodes.get(cloudlet_id)
        if not cloudlet:
            return 0.0
            
        warm_containers = cloudlet.warm_containers
        cold_starts = max(0, num_users - warm_containers)
        return cold_starts * 50.0  # 50ms penalty per cold start

    def calculate_total_objective_function(self) -> Dict[str, float]:
        """
        Calculate the total objective function value for current assignments
        Returns: total_turnaround_time, total_migration_cost, total_cold_start_penalty, total_cost
        """
        total_turnaround_time = 0.0
        total_migration_cost = 0.0
        total_cold_start_penalty = 0.0
        
        # Count users per cloudlet for cold start calculation
        cloudlet_user_count = defaultdict(int)
        
        # Calculate turnaround time and migration costs
        for user_id, user_node in self.user_nodes.items():
            # Turnaround latency cost
            turnaround_cost = self._calculate_turnaround_latency(user_node, user_node.assigned_node_id)
            total_turnaround_time += turnaround_cost
            
            # Migration cost (if user has previous assignment)
            if user_node.previous_node_id and user_node.previous_node_id != user_node.assigned_node_id:
                migration_cost = self._calculate_migration_cost(user_id, user_node.previous_node_id, user_node.assigned_node_id)
                total_migration_cost += migration_cost
                
            # Count users per cloudlet
            cloudlet_user_count[user_node.assigned_node_id] += 1
        
        # Calculate cold start penalties
        for cloudlet_id, num_users in cloudlet_user_count.items():
            cold_start_penalty = self._calculate_cold_start_penalty(cloudlet_id, num_users)
            total_cold_start_penalty += cold_start_penalty
        
        total_cost = total_turnaround_time + total_migration_cost + total_cold_start_penalty
        
        return {
            "total_turnaround_time": total_turnaround_time,
            "total_migration_cost": total_migration_cost,
            "total_cold_start_penalty": total_cold_start_penalty,
            "total_cost": total_cost,
            "algorithm": self.assignment_algorithm.value,
            "num_users": len(self.user_nodes),
            "num_cloudlets": len(self.edge_nodes) + 1  # +1 for central node
        }

    def get_detailed_assignment_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for each cloudlet including resource utilization"""
        metrics = {}
        cloudlet_assignments = defaultdict(list)
        
        # Group users by assigned cloudlet
        for user_id, user_node in self.user_nodes.items():
            cloudlet_assignments[user_node.assigned_node_id].append(user_node)
        
        # Calculate metrics for each cloudlet
        for cloudlet_id, users in cloudlet_assignments.items():
            num_users = len(users)
            total_memory = sum(u.memory_demand for u in users)
            total_cpu = sum(u.cpu_demand for u in users)
            total_bandwidth = sum(u.bandwidth_demand for u in users)
            
            if cloudlet_id == "central_node":
                memory_utilization = 0.0  # Unlimited capacity
                cpu_utilization = 0.0
                bandwidth_utilization = 0.0
                cold_starts = 0
            else:
                cloudlet = self.edge_nodes.get(cloudlet_id)
                if cloudlet:
                    memory_utilization = (total_memory / cloudlet.memory_capacity) * 100
                    cpu_utilization = (total_cpu / cloudlet.cpu_capacity) * 100
                    bandwidth_utilization = (total_bandwidth / cloudlet.bandwidth_capacity) * 100
                    cold_starts = max(0, num_users - cloudlet.warm_containers)
                else:
                    memory_utilization = cpu_utilization = bandwidth_utilization = 0.0
                    cold_starts = 0
            
            avg_turnaround_time = sum(self._calculate_turnaround_latency(u, cloudlet_id) for u in users) / max(1, num_users)
            
            metrics[cloudlet_id] = {
                "num_users": num_users,
                "memory_utilization_percent": memory_utilization,
                "cpu_utilization_percent": cpu_utilization,
                "bandwidth_utilization_percent": bandwidth_utilization,
                "cold_starts": cold_starts,
                "avg_turnaround_time": avg_turnaround_time,
                "total_memory_demand": total_memory,
                "total_cpu_demand": total_cpu,
                "total_bandwidth_demand": total_bandwidth
            }
        
        return metrics
    
    def _greedy_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        '''
            RULE-BASED GREEDY ASSIGNMENT:
            1. Assign to the nearest healthy node within coverage and resource constraints.
            2. If no healthy node is available, assign to the nearest warning node within coverage.
            3. If no warning node is available, assign to the nearest unhealthy node within coverage.
            4. If no edge node is within coverage, assign to the central node.
        '''
        classified_nodes = self._classify_nodes()
        
        # Create a temporary user node for resource checking
        temp_user = UserNodeInfo(
            user_id="temp",
            assigned_node_id="",
            location=user_location,
            size=10,
            speed=5,
            last_executed=0,
            latency=None,
            bandwidth_demand=10.0,
            memory_demand=128.0,
            cpu_demand=1.0,
            data_size_demand=1024.0
        )
        
        def find_nearest_in_category(node_ids: set) -> Tuple[Optional[str], float]:
            best_node = None
            min_distance = float('inf')
            
            for node_id in node_ids:
                if node_id not in self.edge_nodes:
                    continue
                    
                node = self.edge_nodes[node_id]
                
                # Check coverage constraint
                if not self._check_coverage(user_location, node_id):
                    continue
                    
                # Check resource constraints
                if not self._check_resource_constraints(temp_user, node_id):
                    continue
                    
                distance = self._calculate_distance(user_location, node.location)
                if distance < min_distance:
                    min_distance = distance
                    best_node = node_id
                    
            return best_node, min_distance if best_node else float('inf')
        
        # Try healthy nodes first
        node_id, distance = find_nearest_in_category(classified_nodes["healthy"])
        if node_id:
            return node_id, distance
            
        # Try warning nodes
        node_id, distance = find_nearest_in_category(classified_nodes["warning"])
        if node_id:
            return node_id, distance
            
        # Try unhealthy nodes
        node_id, distance = find_nearest_in_category(classified_nodes["unhealthy"])
        if node_id:
            return node_id, distance
            
        # Fallback to central node
        return "central_node", 1000.0  # Default distance to central node
        
    
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
        
        # For single user assignment, we solve a simplified version
        # In practice, this would be called for the entire user set at each time step
        
        users = list(self.user_nodes.keys()) + ["temp_user"]  # Include current request
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
                # Coverage constraint
                cov[i, j] = 1 if self._check_coverage(user_loc, cloudlet_id) else 0
                
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
        
        # Coverage constraint: only assign to cloudlets in coverage
        for i in range(n_users):
            for j in range(n_cloudlets):
                constraints.append(a[i, j] <= cov[i, j])
        
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

    def get_last_cvx_metrics(self) -> Dict[str, float]:
        """Get metrics from the last CVX optimization run"""
        return {
            "total_objective_value": getattr(self, '_last_cvx_objective_value', 0.0),
            "latency_cost": getattr(self, '_last_cvx_latency_cost', 0.0),
            "cold_start_cost": getattr(self, '_last_cvx_cold_start_cost', 0.0),
            "algorithm": "convex optimization"
        }

    def compare_algorithms_performance(self, user_location: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Compare performance of both algorithms on current assignments
        If user_location provided, also compares assignment decision for new user
        """
        # Store current algorithm
        current_algo = self.assignment_algorithm
        
        # Get current state objective function
        current_objective = self.calculate_total_objective_function()
        detailed_metrics = self.get_detailed_assignment_metrics()
        
        comparison_results = {
            "current_algorithm": current_algo.value,
            "current_performance": current_objective,
            "detailed_cloudlet_metrics": detailed_metrics,
            "timestamp": time.time()
        }
        
        # If a new user location is provided, compare assignment decisions
        if user_location:
            # Test Greedy
            self.assignment_algorithm = AssignmentAlgorithm.GREEDY
            greedy_node, greedy_distance, greedy_metrics = self.node_assignment_with_metrics(user_location)
            
            # Test CVX
            self.assignment_algorithm = AssignmentAlgorithm.CVX
            cvx_node, cvx_distance = self._convex_optimization_assignment(user_location)
            cvx_metrics = self.get_last_cvx_metrics()
            
            # Restore original algorithm
            self.assignment_algorithm = current_algo
            
            comparison_results["new_user_comparison"] = {
                "user_location": user_location,
                "greedy_assignment": {
                    "assigned_node": greedy_node,
                    "distance": greedy_distance,
                    "estimated_turnaround_time": greedy_metrics["estimated_turnaround_time"],
                    "estimated_cold_start_penalty": greedy_metrics["estimated_cold_start_penalty"]
                },
                "cvx_assignment": {
                    "assigned_node": cvx_node,
                    "distance": cvx_distance,
                    "optimization_objective_value": cvx_metrics["total_objective_value"],
                    "latency_cost": cvx_metrics["latency_cost"],
                    "cold_start_cost": cvx_metrics["cold_start_cost"]
                },
                "algorithm_agreement": greedy_node == cvx_node,
                "performance_difference": {
                    "turnaround_time_diff": greedy_metrics["estimated_turnaround_time"] - cvx_metrics["latency_cost"],
                    "cold_start_diff": greedy_metrics["estimated_cold_start_penalty"] - cvx_metrics["cold_start_cost"]
                }
            }
        
        return comparison_results

    def get_performance_summary_for_frontend(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics formatted for frontend display
        """
        objective = self.calculate_total_objective_function()
        detailed = self.get_detailed_assignment_metrics()
        
        # Calculate overall utilization statistics
        total_users = sum(metrics["num_users"] for metrics in detailed.values())
        avg_memory_util = sum(metrics["memory_utilization_percent"] for metrics in detailed.values()) / max(1, len(detailed))
        avg_cpu_util = sum(metrics["cpu_utilization_percent"] for metrics in detailed.values()) / max(1, len(detailed))
        avg_bandwidth_util = sum(metrics["bandwidth_utilization_percent"] for metrics in detailed.values()) / max(1, len(detailed))
        total_cold_starts = sum(metrics["cold_starts"] for metrics in detailed.values())
        
        return {
            "algorithm": objective["algorithm"],
            "performance_metrics": {
                "total_cost": round(objective["total_cost"], 2),
                "total_turnaround_time": round(objective["total_turnaround_time"], 2),
                "total_migration_cost": round(objective["total_migration_cost"], 2),
                "total_cold_start_penalty": round(objective["total_cold_start_penalty"], 2)
            },
            "resource_utilization": {
                "total_users": total_users,
                "avg_memory_utilization": round(avg_memory_util, 1),
                "avg_cpu_utilization": round(avg_cpu_util, 1),
                "avg_bandwidth_utilization": round(avg_bandwidth_util, 1),
                "total_cold_starts": total_cold_starts
            },
            "cloudlet_breakdown": detailed,
            "timestamp": time.time()
        }
        