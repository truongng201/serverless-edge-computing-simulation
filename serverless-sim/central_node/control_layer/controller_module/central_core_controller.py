import logging
from typing import Dict, Any
import time

from central_node.api_layer.central_controller import CentralNodeAPIController

from central_node.control_layer.scheduler_module.scheduler import Scheduler, EdgeNodeInfo, UserNodeInfo
from central_node.control_layer.agents_module.scheduler_agent import SchedulerAgent
from central_node.control_layer.prediction_module.prediction import WorkloadPredictor
from central_node.control_layer.metrics_module.global_metrics import NodeMetrics


class CentralCoreController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize control layer components
        self.scheduler = Scheduler()
        self.predictor = WorkloadPredictor()
        self.central_node_api_controller = CentralNodeAPIController()
        SchedulerAgent(self.scheduler).start_all_tasks()


    def schedule_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a request to an edge node"""
        try:
            decision = self.scheduler.schedule_request(request_data)
            
            if not decision:
                return {
                    "success": False,
                    "error": "No available edge nodes",
                    "code": "NO_NODES_AVAILABLE"
                }
                
            return {
                "success": True,
                "target_node": decision.target_node_id,
                "estimated_time": decision.execution_time_estimate,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            self.logger.error(f"Request scheduling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "SCHEDULING_ERROR"
            }
            
    def register_edge_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new edge node"""
        try:
            node_metrics = NodeMetrics(
                node_id=node_data["node_id"],
                cpu_usage=0.0,
                memory_usage=0.0,
                memory_total=0,
                running_container=0,
                warm_container=0,
                active_requests=0,
                total_requests=0,
                response_time_avg=0.0,
                energy_consumption=0.0,
                load_average=[],
                network_io={},
                disk_io={},
                timestamp=0,
                uptime=0
            )

            node_info = EdgeNodeInfo(
                node_id=node_data["node_id"],
                endpoint=node_data["endpoint"],
                location=node_data.get("location", {"x": 0.0, "y": 0.0}),
                system_info=node_data.get("system_info", {}),
                last_heartbeat=time.time(),
                metrics_info=node_metrics
            )
            
            self.scheduler.register_edge_node(node_info)
            
            return {
                "success": True,
                "message": f"Edge node {node_data['node_id']} registered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Node registration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "REGISTRATION_ERROR"
            }
            
    def update_node_metrics(self, node_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Add to global metrics collection
            node_metrics = NodeMetrics(
                node_id=node_id,
                cpu_usage=request_data.get("cpu_usage", 0.0),
                memory_usage=request_data.get("memory_usage", 0.0),
                memory_total=request_data.get("memory_total", 0),
                running_container=request_data.get("running_container", 0),
                warm_container=request_data.get("warm_container", 0),
                active_requests=request_data.get("active_requests", 0),
                total_requests=request_data.get("total_requests", 0),
                response_time_avg=request_data.get("response_time_avg", 0.0),
                energy_consumption=request_data.get("energy_consumption", 0.0),
                load_average=request_data.get("load_average", []),
                network_io=request_data.get("network_io", {}),
                disk_io=request_data.get("disk_io", {}),
                timestamp=request_data.get("timestamp", 0),
                uptime=request_data.get("uptime", 0)
            )
            system_info = request_data.get("system_info", {})
            endpoint = request_data.get("endpoint", "")

            self.scheduler.update_node_metrics(node_id, node_metrics, system_info, endpoint)

            # Log the heartbeat
            self.logger.debug(f"Received metrics from node {node_id}: CPU={request_data.get('cpu_usage', 0):.1f}%, Memory={request_data.get('memory_usage', 0):.1f}%")
            
            return {
                "success": True,
                "message": f"Metrics for node {node_id} updated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Metrics update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "METRICS_ERROR"
            }
            
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status including central node metrics"""
        try:
            scheduler_status = self.scheduler.get_cluster_status()
            central_node_status = self.central_node_api_controller.get_central_node_status()
            central_node_status["location"] = self.scheduler.get_central_node_info().get("location", {"x": 0.0, "y": 0.0})
            central_node_status["coverage"] = self.scheduler.get_central_node_info().get("coverage", 0)
            return {
                "success": True,
                "central_node": central_node_status,
                "cluster_info": scheduler_status,
                "timestamp": time.time()
            }
            
        except Exception as e:
            
            self.logger.error(f"Cluster status failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "code": "STATUS_ERROR"
            }
            
    def predict_workload(self, node_id: str, horizon_minutes: int = 30) -> Dict[str, Any]:
        """Get workload prediction for a node"""
        try:
            prediction = self.predictor.predict_workload(node_id, horizon_minutes)
            
            if not prediction:
                return {
                    "success": False,
                    "error": "Prediction not available",
                    "code": "PREDICTION_ERROR"
                }
                
            return {
                "success": True,
                "prediction": {
                    "predicted_load": prediction.predicted_load,
                    "confidence_interval": prediction.confidence_interval,
                    "horizon_minutes": prediction.prediction_horizon,
                    "accuracy": prediction.model_accuracy
                }
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "PREDICTION_ERROR"
            }

    def update_edge_node(self, data):
        new_location = data.get("location", None)
        
        if not new_location:
            return None

        # Update the node's location
        edge_node = self.scheduler.edge_nodes.get(data.get("node_id", None))
        print(edge_node)
        if not edge_node:
            return None

        edge_node.location = new_location
        self.scheduler.update_edge_node_info(edge_node)

        return edge_node
    
    def create_user_node(self, data):
        user_location = data.get("location", {"x": 0.0, "y": 0.0})
        
        # Find nearest node (edge or central)
        nearest_node_id = self._find_nearest_node(user_location)
        
        user_node = UserNodeInfo(
            user_id=data.get("user_id"),
            assigned_node_id=nearest_node_id,
            location=user_location,
            size=data.get("size", 10),
            speed=data.get("speed", 5)
        )
        self.scheduler.create_user_node(user_node)
        return user_node
    
    def _find_nearest_node(self, user_location):
        """Find the nearest node (edge or central) to the user location"""
        min_distance = float('inf')
        nearest_node_id = "central_node"  # default to central node
        
        # Check all edge nodes
        for node_id, edge_node in self.scheduler.edge_nodes.items():
            distance = self._calculate_distance(
                user_location, 
                edge_node.location
            )
            if distance < min_distance:
                min_distance = distance
                nearest_node_id = node_id
        
        # Check central node
        central_node = self.scheduler.get_central_node_info()
        central_distance = self._calculate_distance(
            user_location,
            central_node["location"]
        )
        if central_distance < min_distance:
            nearest_node_id = "central_node"
        
        return nearest_node_id
    
    def _calculate_distance(self, location1, location2):
        """Calculate Euclidean distance between two locations"""
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def get_all_users(self):
        """Get all user nodes"""
        try:
            users = []
            for user_id, user_node in self.scheduler.user_nodes.items():
                # Determine if assigned to edge or central node
                assigned_edge = None
                assigned_central = None
                
                if user_node.assigned_node_id == "central_node":
                    assigned_central = "central_node"
                elif user_node.assigned_node_id in self.scheduler.edge_nodes:
                    assigned_edge = user_node.assigned_node_id
                
                users.append({
                    "user_id": user_id,
                    "location": user_node.location,
                    "size": user_node.size,
                    "speed": user_node.speed,
                    "assigned_node_id": user_node.assigned_node_id,
                    "assigned_edge": assigned_edge,
                    "assigned_central": assigned_central,
                    "latency": 0  # Can be calculated if needed
                })
            
            return {
                "success": True,
                "users": users,
                "total_count": len(users)
            }
        except Exception as e:
            self.logger.error(f"Error getting all users: {e}")
            return {
                "success": False,
                "error": str(e),
                "users": []
            }