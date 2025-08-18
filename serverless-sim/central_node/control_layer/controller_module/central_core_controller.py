import logging
from typing import Dict, Any
import time
import random

from central_node.api_layer.central_controller import CentralNodeAPIController
from central_node.api_layer.central_agent import CentralNodeAPIAgent

from central_node.control_layer.scheduler_module.scheduler import Scheduler, EdgeNodeInfo, UserNodeInfo, Latency
from central_node.control_layer.agents_module.scheduler_agent import SchedulerAgent
from central_node.control_layer.agents_module.users_agent import UsersAgent
from central_node.control_layer.prediction_module.prediction import WorkloadPredictor
from central_node.control_layer.metrics_module.global_metrics import NodeMetrics

from config import Config


class CentralCoreController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize control layer components
        self.scheduler = Scheduler()
        self.predictor = WorkloadPredictor()
        self.central_node_api_controller = CentralNodeAPIController()
        CentralNodeAPIAgent(self.central_node_api_controller).start_all_tasks()
        SchedulerAgent(self.scheduler).start_all_tasks()
        UsersAgent(self.scheduler).start_all_tasks()


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
        if not edge_node:
            return None

        edge_node.location = new_location
        self.scheduler.update_edge_node_info(edge_node)

        return edge_node
    
    def create_user_node(self, data):
        user_location = data.get("location", {"x": 0.0, "y": 0.0})
        
        # Find nearest node (edge or central) using scheduler method
        nearest_node_id, nearest_distance = self.scheduler._find_nearest_node(user_location)
        data_size = random.randint(*Config.DEFAULT_RANDOM_DATA_SIZE_RANGE_IN_BYTES)
        bandwidth = random.randint(*Config.DEFAULT_RANDOM_BANDWIDTH_RANGE_IN_BYTES_PER_MILLISECOND)
        propagation_delay = nearest_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000  # Convert to ms
        transmission_delay = data_size / bandwidth
        total_turnaround_time = propagation_delay + transmission_delay
        latency = Latency(
            distance=nearest_distance,
            data_size=data_size,
            bandwidth=bandwidth,
            propagation_delay=propagation_delay,
            transmission_delay=transmission_delay,
            computation_delay=0.0,
            container_status="unknown",
            total_turnaround_time=total_turnaround_time
        )
        user_node = UserNodeInfo(
            user_id=data.get("user_id"),
            assigned_node_id=nearest_node_id,
            location=user_location,
            last_executed=0,
            size=data.get("size", 10),
            speed=data.get("speed", 5),
            latency=latency
        )
        self.scheduler.create_user_node(user_node)
        return user_node
    
    def update_user_node(self, data):
        """Update user node location and recalculate assigned node"""
        try:
            user_id = data.get("user_id")
            new_location = data.get("location", {})
            
            if not user_id:
                self.logger.error("User ID is required for user node update")
                return {
                    "success": False,
                    "error": "User ID is required"
                }
            
            if not new_location or "x" not in new_location or "y" not in new_location:
                self.logger.error("Valid location (x, y) is required for user node update")
                return {
                    "success": False,
                    "error": "Valid location (x, y) is required"
                }
            
            # Update user node in scheduler
            success = self.scheduler.update_user_node(user_id, new_location)
            
            if success:
                # Get updated user info
                updated_user = self.scheduler.user_nodes.get(user_id)
                if updated_user:
                    return {
                        "success": True,
                        "message": f"User {user_id} updated successfully",
                        "user": {
                            "user_id": updated_user.user_id,
                            "location": updated_user.location,
                            "assigned_node_id": updated_user.assigned_node_id,
                            "size": updated_user.size,
                            "speed": updated_user.speed,
                            "latency": updated_user.latency
                        }
                    }
            
            return {
                "success": False,
                "error": f"Failed to update user {user_id}"
            }
            
        except Exception as e:
            self.logger.error(f"Error updating user node: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
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
                user_node.latency.total_turnaround_time = user_node.latency.propagation_delay + user_node.latency.transmission_delay + user_node.latency.computation_delay
                users.append({
                    "user_id": user_id,
                    "location": user_node.location,
                    "size": user_node.size,
                    "speed": user_node.speed,
                    "assigned_node_id": user_node.assigned_node_id,
                    "assigned_edge": assigned_edge,
                    "assigned_central": assigned_central,
                    "last_executed_period": time.time() - user_node.last_executed,
                    "latency": user_node.latency
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
            
    def execute_function(self, data):
        try:
            return self.central_node_api_controller.execute_function(data)
        except Exception as e:
            self.logger.error(f"Error executing function: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def delete_all_users(self):
        try:
            self.scheduler.user_nodes.clear()
            return {
                "success": True,
                "message": "All user nodes deleted successfully"
            }
        except Exception as e:
            self.logger.error(f"Error deleting all user nodes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def delete_user(self, user_id: str):
        try:
            if user_id not in self.scheduler.user_nodes:
                return {
                    "success": False,
                    "error": f"User {user_id} not found"
                }

            del self.scheduler.user_nodes[user_id]
            return {
                "success": True,
                "message": f"User {user_id} deleted successfully"
            }
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }