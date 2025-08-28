"""
Central Node Control Layer - Scheduler Module
Handles scheduling decisions, load balancing, and request routing
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from config import Config

from central_node.control_layer.metrics_module.global_metrics import NodeMetrics
from central_node.control_layer.scheduler_module.gap_solver import GAPSolver, GAPConfig

class SchedulingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    GEOGRAPHIC = "geographic"
    PREDICTIVE = "predictive"
    GAP_BASELINE = "gap_baseline"

@dataclass
class Latency:
    distance: float
    data_size: float
    bandwidth: float
    propagation_delay: float
    transmission_delay: float
    computation_delay: float
    container_status: str
    total_turnaround_time: float

@dataclass
class EdgeNodeInfo:
    node_id: str
    endpoint: str
    location: Dict[str, float]  # {"x": ..., "y": ...}
    system_info: Dict[str, Any]
    last_heartbeat: float
    metrics_info: NodeMetrics
    coverage: float

@dataclass
class UserNodeInfo:
    user_id: str
    assigned_node_id: str
    location: Dict[str, float]  # {"x": ..., "y": ...}
    size: int
    speed: int
    last_executed: float
    latency: Latency

@dataclass
class SchedulingDecision:
    target_node_id: str
    execution_time_estimate: float
    confidence: float
    reasoning: str

class Scheduler:
    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.edge_nodes: Dict[str, EdgeNodeInfo] = {}
        self.central_node = {
            "node_id": "central_node",
            "endpoint": "localhost:8000",
            "location": {"x": 600, "y": 400}, # default location
            "coverage": 0 # default coverage
        }
        self.user_nodes: Dict[str, UserNodeInfo] = {}
        self.round_robin_index = 0
        self.logger = logging.getLogger(__name__)
        
        # Initialize GAP solver
        self.gap_solver = GAPSolver(GAPConfig(debug_logging=True))
        self.simulation = False

    def start_simulation(self):
        self.simulation = True
        
    def stop_simulation(self):
        self.simulation = False

    def get_central_node_info(self) -> Dict[str, Any]:
        return self.central_node
    
    def set_scheduling_strategy(self, strategy: SchedulingStrategy):
        """Change the scheduling strategy"""
        self.strategy = strategy
        self.logger.info(f"Scheduling strategy changed to: {strategy.value}")
        
    def get_scheduling_strategy(self) -> str:
        """Get current scheduling strategy"""
        return self.strategy.value
    
    def create_user_node(self, user_node: UserNodeInfo):
        self.user_nodes[user_node.user_id] = user_node

    def register_edge_node(self, node_info: EdgeNodeInfo):
        if node_info.node_id in self.edge_nodes:
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

    def schedule_request(self, request_data: Dict[str, Any]) -> Optional[SchedulingDecision]:
        """Schedule a request to the best available edge node"""
        available_nodes = []
        
        if not available_nodes:
            self.logger.warning("No healthy edge nodes available")
            return None
            
        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._schedule_round_robin(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.LEAST_LOADED:
            return self._schedule_least_loaded(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.GEOGRAPHIC:
            return self._schedule_geographic(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.PREDICTIVE:
            return self._schedule_predictive(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.GAP_BASELINE:
            return self._schedule_gap_baseline(available_nodes, request_data)
        else:
            return self._schedule_round_robin(available_nodes, request_data)

    def _schedule_round_robin(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Round robin scheduling"""
        if self.round_robin_index >= len(nodes):
            self.round_robin_index = 0
            
        selected_node = nodes[self.round_robin_index]
        self.round_robin_index += 1
        
        return SchedulingDecision(
            target_node_id=selected_node.node_id,
            execution_time_estimate=1.0,  # Default estimate
            confidence=0.8,
            reasoning="Round robin selection"
        )
        
    def _schedule_least_loaded(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Least loaded scheduling"""
        selected_node = min(nodes, key=lambda n: n.current_load)
        
        return SchedulingDecision(
            target_node_id=selected_node.node_id,
            execution_time_estimate=1.0 / (1.0 - selected_node.current_load),
            confidence=0.9,
            reasoning=f"Least loaded node (load: {selected_node.current_load:.2f})"
        )
        
    def _schedule_geographic(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Geographic-based scheduling"""
        # For now, just use least loaded
        # TODO: Implement actual geographic distance calculation
        return self._schedule_least_loaded(nodes, request_data)
        
    def _schedule_predictive(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Predictive scheduling using ML models"""
        # For now, just use least loaded
        # TODO: Integrate with prediction module
        return self._schedule_least_loaded(nodes, request_data)
    
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

    def update_edge_node_info(self, new_edge_node: EdgeNodeInfo):
        if new_edge_node.node_id not in self.edge_nodes:
            return
        self.edge_nodes[new_edge_node.node_id] = new_edge_node
    
    def update_user_node(self, user_id: str, new_location: Dict[str, float]) -> bool:
        """Update user node location and reassign to nearest node"""
        if user_id not in self.user_nodes:
            return False
        
        # Update location
        self.user_nodes[user_id].location = new_location
        
        # Recalculate nearest node
        nearest_node_id, nearest_distance = self._node_assignment(new_location)
        self.user_nodes[user_id].assigned_node_id = nearest_node_id
        self.user_nodes[user_id].latency.distance = nearest_distance
        
        self.logger.info(f"Updated user {user_id} location to {new_location}, assigned to {nearest_node_id}")
        return True
    
    def _node_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        min_distance = self._calculate_distance(user_location, self.central_node["location"])
        nearest_node_id = "central_node"  # default to central node
        
        # Check all edge nodes
        for node_id, edge_node in self.edge_nodes.items():
            distance = self._calculate_distance(user_location, edge_node.location)
            if distance < min_distance and distance <= edge_node.coverage:
                min_distance = distance
                nearest_node_id = node_id

        return nearest_node_id, min_distance * Config.DEFAULT_PIXEL_TO_METERS

    def _calculate_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        """Calculate Euclidean distance between two locations"""
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def _schedule_gap_baseline(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """GAP-based scheduling using utility optimization"""
        user_id = request_data.get('user_id', 'unknown_user')
        user_location = request_data.get('user_location', {'x': 0, 'y': 0})
        
        try:
            # Prepare data for GAP solver
            users = {
                user_id: {
                    'location': user_location,
                    'data_size': request_data.get('data_size', 300)  # MB
                }
            }
            
            # Convert edge nodes to GAP format
            edge_nodes = {}
            for node in nodes:
                edge_nodes[node.node_id] = {
                    'node_id': node.node_id,
                    'location': node.location,
                    'endpoint': node.endpoint,
                    'metrics': node.metrics_info.__dict__ if node.metrics_info else {}
                }
            
            # Run GAP solver
            assignments = self.gap_solver.solve_gap(users, edge_nodes, self.central_node)
            
            if assignments and len(assignments) > 0:
                assignment = assignments[0]  # Get assignment for our user
                
                # Log GAP statistics
                stats = self.gap_solver.get_assignment_stats(assignments)
                self.logger.info(f"GAP assignment stats: {stats}")
                
                return SchedulingDecision(
                    target_node_id=assignment.target_node_id,
                    execution_time_estimate=assignment.estimated_latency / 1000.0,  # Convert to seconds
                    confidence=0.9,  # High confidence in GAP optimization
                    reasoning=assignment.reasoning
                )
            else:
                # Fallback to round robin if GAP fails
                self.logger.warning("GAP assignment failed, falling back to round robin")
                return self._schedule_round_robin(nodes, request_data)
                
        except Exception as e:
            self.logger.error(f"GAP scheduling error: {e}")
            # Fallback to round robin
            return self._schedule_round_robin(nodes, request_data)