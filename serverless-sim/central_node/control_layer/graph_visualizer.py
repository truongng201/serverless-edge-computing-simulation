"""
Central Node Control Layer - Graph Visualization
Provides graph-based visualization of the serverless cluster
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class GraphNode:
    id: str
    label: str
    type: str  # "central", "edge", "function", "request"
    position: Dict[str, float]  # {"x": ..., "y": ...}
    data: Dict[str, Any]
    status: str  # "healthy", "warning", "error", "idle"

@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    label: str
    type: str  # "control", "data", "migration", "heartbeat"
    weight: float
    data: Dict[str, Any]

class GraphVisualizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        
        # Add central node
        self._add_central_node()
        
    def _add_central_node(self):
        """Add the central node to the graph"""
        central_node = GraphNode(
            id="central_node",
            label="Central Node",
            type="central",
            position={"x": 0, "y": 0},
            data={
                "components": ["scheduler", "predictor", "migration_manager", "metrics_collector"],
                "api_endpoints": ["/schedule", "/nodes/register", "/cluster/status"]
            },
            status="healthy"
        )
        self.nodes["central_node"] = central_node
        
    def add_edge_node(self, node_id: str, endpoint: str, location: Dict[str, float], 
                     status: str = "healthy", metrics: Dict[str, Any] = None):
        """Add an edge node to the graph"""
        # Position edge nodes in a circle around central node
        import math
        angle = hash(node_id) % 360
        radius = 200
        x = radius * math.cos(math.radians(angle))
        y = radius * math.sin(math.radians(angle))
        
        edge_node = GraphNode(
            id=node_id,
            label=f"Edge Node {node_id}",
            type="edge",
            position={"x": x, "y": y},
            data={
                "endpoint": endpoint,
                "location": location,
                "metrics": metrics or {},
                "containers": []
            },
            status=status
        )
        self.nodes[node_id] = edge_node
        
        # Add connection to central node
        edge_id = f"central_to_{node_id}"
        connection = GraphEdge(
            id=edge_id,
            source="central_node",
            target=node_id,
            label="Control Channel",
            type="control",
            weight=1.0,
            data={"last_heartbeat": None, "latency": 0}
        )
        self.edges[edge_id] = connection
        
    def add_function_container(self, node_id: str, container_id: str, 
                             function_id: str, state: str, metrics: Dict[str, Any] = None):
        """Add a function container to the graph"""
        if node_id not in self.nodes:
            self.logger.warning(f"Node {node_id} not found, cannot add container")
            return
            
        # Position container near its parent node
        parent_node = self.nodes[node_id]
        container_x = parent_node.position["x"] + (hash(container_id) % 50 - 25)
        container_y = parent_node.position["y"] + (hash(container_id) % 50 - 25)
        
        container_node = GraphNode(
            id=container_id,
            label=f"Function {function_id}",
            type="function",
            position={"x": container_x, "y": container_y},
            data={
                "function_id": function_id,
                "state": state,
                "metrics": metrics or {},
                "parent_node": node_id
            },
            status=self._container_state_to_status(state)
        )
        self.nodes[container_id] = container_node
        
        # Add edge from node to container
        edge_id = f"{node_id}_to_{container_id}"
        container_edge = GraphEdge(
            id=edge_id,
            source=node_id,
            target=container_id,
            label="Hosts",
            type="hosting",
            weight=1.0,
            data={"state": state}
        )
        self.edges[edge_id] = container_edge
        
    def add_request_flow(self, request_id: str, source_node: str, target_node: str, 
                        function_id: str, status: str = "active"):
        """Add a request flow to the graph"""
        request_node = GraphNode(
            id=request_id,
            label=f"Request {request_id[:8]}",
            type="request",
            position={"x": 0, "y": -100},  # Position between nodes
            data={
                "function_id": function_id,
                "source": source_node,
                "target": target_node,
                "status": status
            },
            status=status
        )
        self.nodes[request_id] = request_node
        
        # Add edges for request flow
        request_in_edge = GraphEdge(
            id=f"request_in_{request_id}",
            source=source_node,
            target=request_id,
            label="Request",
            type="data",
            weight=2.0,
            data={"direction": "inbound"}
        )
        self.edges[f"request_in_{request_id}"] = request_in_edge
        
        request_out_edge = GraphEdge(
            id=f"request_out_{request_id}",
            source=request_id,
            target=target_node,
            label="Execute",
            type="data",
            weight=2.0,
            data={"direction": "outbound"}
        )
        self.edges[f"request_out_{request_id}"] = request_out_edge
        
    def add_migration_flow(self, migration_id: str, container_id: str, 
                          source_node: str, target_node: str, status: str = "in_progress"):
        """Add a migration flow to the graph"""
        migration_edge = GraphEdge(
            id=migration_id,
            source=source_node,
            target=target_node,
            label=f"Migrating {container_id[:8]}",
            type="migration",
            weight=3.0,
            data={
                "container_id": container_id,
                "status": status,
                "direction": "migration"
            }
        )
        self.edges[migration_id] = migration_edge
        
    def update_node_metrics(self, node_id: str, metrics: Dict[str, Any]):
        """Update node metrics and status"""
        if node_id not in self.nodes:
            return
            
        node = self.nodes[node_id]
        node.data["metrics"] = metrics
        
        # Update status based on metrics
        cpu_usage = metrics.get("cpu_usage", 0)
        memory_usage = metrics.get("memory_usage", 0)
        
        if cpu_usage > 0.9 or memory_usage > 0.9:
            node.status = "error"
        elif cpu_usage > 0.7 or memory_usage > 0.7:
            node.status = "warning"
        else:
            node.status = "healthy"
            
    def remove_node(self, node_id: str):
        """Remove a node and its edges"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            
        # Remove associated edges
        edges_to_remove = [
            edge_id for edge_id, edge in self.edges.items()
            if edge.source == node_id or edge.target == node_id
        ]
        for edge_id in edges_to_remove:
            del self.edges[edge_id]
            
    def remove_edge(self, edge_id: str):
        """Remove an edge"""
        if edge_id in self.edges:
            del self.edges[edge_id]
            
    def _container_state_to_status(self, state: str) -> str:
        """Convert container state to status color"""
        state_mapping = {
            "running": "healthy",
            "idle": "warning",
            "cold_start": "idle",
            "dead": "error"
        }
        return state_mapping.get(state, "idle")
        
    def get_graph_data(self) -> Dict[str, Any]:
        """Get graph data for visualization"""
        return {
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [asdict(edge) for edge in self.edges.values()],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": self._get_node_type_counts(),
                "edge_types": self._get_edge_type_counts()
            }
        }
        
    def _get_node_type_counts(self) -> Dict[str, int]:
        """Get count of each node type"""
        type_counts = {}
        for node in self.nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        return type_counts
        
    def _get_edge_type_counts(self) -> Dict[str, int]:
        """Get count of each edge type"""
        type_counts = {}
        for edge in self.edges.values():
            type_counts[edge.type] = type_counts.get(edge.type, 0) + 1
        return type_counts
        
    def get_graph_json(self) -> str:
        """Get graph data as JSON string"""
        return json.dumps(self.get_graph_data(), indent=2)
        
    def get_cluster_topology(self) -> Dict[str, Any]:
        """Get cluster topology summary"""
        edge_nodes = [node for node in self.nodes.values() if node.type == "edge"]
        function_containers = [node for node in self.nodes.values() if node.type == "function"]
        active_requests = [node for node in self.nodes.values() if node.type == "request"]
        
        # Calculate connectivity
        total_connections = len(self.edges)
        control_connections = len([e for e in self.edges.values() if e.type == "control"])
        data_connections = len([e for e in self.edges.values() if e.type == "data"])
        
        return {
            "summary": {
                "edge_nodes": len(edge_nodes),
                "function_containers": len(function_containers),
                "active_requests": len(active_requests),
                "total_connections": total_connections
            },
            "connectivity": {
                "control_channels": control_connections,
                "data_flows": data_connections,
                "avg_connections_per_node": total_connections / len(self.nodes) if self.nodes else 0
            },
            "health_distribution": self._get_health_distribution(),
            "load_distribution": self._get_load_distribution()
        }
        
    def _get_health_distribution(self) -> Dict[str, int]:
        """Get distribution of node health statuses"""
        health_dist = {}
        for node in self.nodes.values():
            health_dist[node.status] = health_dist.get(node.status, 0) + 1
        return health_dist
        
    def _get_load_distribution(self) -> Dict[str, float]:
        """Get load distribution across edge nodes"""
        load_dist = {}
        for node in self.nodes.values():
            if node.type == "edge" and "metrics" in node.data:
                cpu_usage = node.data["metrics"].get("cpu_usage", 0)
                load_dist[node.id] = cpu_usage
        return load_dist
        
    def generate_force_directed_layout(self) -> Dict[str, Any]:
        """Generate force-directed layout coordinates"""
        # Simple force-directed algorithm
        import math
        import random
        
        # Initialize positions if not set
        for node in self.nodes.values():
            if not node.position or (node.position["x"] == 0 and node.position["y"] == 0 and node.id != "central_node"):
                node.position = {
                    "x": random.uniform(-300, 300),
                    "y": random.uniform(-300, 300)
                }
        
        # Apply forces (simplified version)
        for iteration in range(50):  # 50 iterations
            forces = {node_id: {"x": 0, "y": 0} for node_id in self.nodes.keys()}
            
            # Repulsion between all nodes
            for node1_id, node1 in self.nodes.items():
                for node2_id, node2 in self.nodes.items():
                    if node1_id != node2_id:
                        dx = node1.position["x"] - node2.position["x"]
                        dy = node1.position["y"] - node2.position["y"]
                        distance = math.sqrt(dx*dx + dy*dy) or 1
                        
                        repulsion = 1000 / (distance * distance)
                        forces[node1_id]["x"] += (dx / distance) * repulsion
                        forces[node1_id]["y"] += (dy / distance) * repulsion
            
            # Attraction along edges
            for edge in self.edges.values():
                source = self.nodes[edge.source]
                target = self.nodes[edge.target]
                
                dx = target.position["x"] - source.position["x"]
                dy = target.position["y"] - source.position["y"]
                distance = math.sqrt(dx*dx + dy*dy) or 1
                
                attraction = distance * 0.01
                forces[edge.source]["x"] += (dx / distance) * attraction
                forces[edge.source]["y"] += (dy / distance) * attraction
                forces[edge.target]["x"] -= (dx / distance) * attraction
                forces[edge.target]["y"] -= (dy / distance) * attraction
            
            # Apply forces with damping
            damping = 0.9
            for node_id, node in self.nodes.items():
                if node_id != "central_node":  # Keep central node fixed
                    node.position["x"] += forces[node_id]["x"] * damping
                    node.position["y"] += forces[node_id]["y"] * damping
        
        return self.get_graph_data()
