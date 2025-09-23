import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import time
from enum import Enum

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
        assigned_node_id, assigned_node_distance = self._node_assignment(new_location)
        self.user_nodes[user_id].assigned_node_id = assigned_node_id
        self.user_nodes[user_id].latency.distance = assigned_node_distance
        
        return True

    def create_user_node(self, user_node: UserNodeInfo):
        self.user_nodes[user_node.user_id] = user_node

    def schedule_request(self, request_data: Dict[str, Any]):
        available_nodes = []
        
        if not available_nodes:
            self.logger.warning("No healthy edge nodes available")
            return None
            
        if self.assignment_algorithm == AssignmentAlgorithm.GREEDY:
            pass
        
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
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5