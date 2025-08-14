"""
Central Node Control Layer - Scheduler Module
Handles scheduling decisions, load balancing, and request routing
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from config import Config, NodeType

class SchedulingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    GEOGRAPHIC = "geographic"
    PREDICTIVE = "predictive"

@dataclass
class EdgeNodeInfo:
    node_id: str
    endpoint: str
    location: Dict[str, float]  # {"x": ..., "y": ...}
    current_load: float
    available_resources: Dict[str, Any]
    last_heartbeat: float

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
        self.round_robin_index = 0
        self.logger = logging.getLogger(__name__)
        
    def register_edge_node(self, node_info: EdgeNodeInfo):
        """Register a new edge node"""
        self.edge_nodes[node_info.node_id] = node_info
        self.logger.info(f"Registered edge node: {node_info.node_id}")
        
    def unregister_edge_node(self, node_id: str):
        """Unregister an edge node"""
        if node_id in self.edge_nodes:
            del self.edge_nodes[node_id]
            self.logger.info(f"Unregistered edge node: {node_id}")
            
    def update_node_metrics(self, node_id: str, metrics: Dict[str, Any]):
        """Update node metrics from heartbeat"""
        print(metrics)
        if node_id in self.edge_nodes:
            self.edge_nodes[node_id].current_load = metrics.get('cpu_usage', 0.0)
            self.edge_nodes[node_id].available_resources = metrics.get('resources', {})
            self.edge_nodes[node_id].last_heartbeat = time.time()
            
        # Clean up dead nodes after each update
        self._cleanup_dead_nodes()
            
    def _cleanup_dead_nodes(self):
        """Remove nodes that haven't sent heartbeat for too long"""
        current_time = time.time()
        dead_nodes = []
        
        for node_id, node in self.edge_nodes.items():
            if current_time - node.last_heartbeat > 10: # 10 seconds time out
                dead_nodes.append(node_id)
                
        for node_id in dead_nodes:
            self.logger.warning(f"Removing dead node: {node_id} (last seen: {current_time - self.edge_nodes[node_id].last_heartbeat:.1f}s ago)")
            del self.edge_nodes[node_id]
            
    def schedule_request(self, request_data: Dict[str, Any]) -> Optional[SchedulingDecision]:
        """Schedule a request to the best available edge node"""
        available_nodes = self._get_healthy_nodes()
        
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
        else:
            return self._schedule_round_robin(available_nodes, request_data)
            
    def _get_healthy_nodes(self) -> List[EdgeNodeInfo]:
        """Get list of healthy edge nodes"""
        current_time = time.time()
        healthy_nodes = []
        
        for node in self.edge_nodes.values():
            if current_time - node.last_heartbeat < 60:  # 1 minute timeout (consistent with cleanup)
                healthy_nodes.append(node)
                
        return healthy_nodes
        
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
        
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        healthy_nodes = self._get_healthy_nodes()
        total_load = sum(node.current_load for node in healthy_nodes)
        avg_load = total_load / len(healthy_nodes) if healthy_nodes else 0
        
        current_time = time.time()
        all_nodes_info = []
        unhealthy_nodes = []
        
        for node in self.edge_nodes.values():
            last_seen = current_time - node.last_heartbeat
            is_healthy = last_seen < 60
            
            node_info = {
                "node_id": node.node_id,
                "load": node.current_load,
                "location": node.location,
                "last_seen": last_seen,
                "status": "healthy" if is_healthy else "unhealthy",
                "endpoint": node.endpoint
            }
            
            all_nodes_info.append(node_info)
            if not is_healthy:
                unhealthy_nodes.append(node_info)
        
        return {
            "total_nodes": len(self.edge_nodes),
            "healthy_nodes": len(healthy_nodes),
            "unhealthy_nodes": len(unhealthy_nodes),
            "average_load": avg_load,
            "nodes": all_nodes_info,
            "healthy_nodes_list": [node.node_id for node in healthy_nodes],
            "unhealthy_nodes_list": [node["node_id"] for node in unhealthy_nodes]
        }
