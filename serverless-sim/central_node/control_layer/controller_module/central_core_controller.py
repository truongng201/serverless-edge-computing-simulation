import logging
from typing import Dict, Any
import time
import random

from central_node.api_layer.central_controller import CentralNodeAPIController
from central_node.api_layer.central_agent import CentralNodeAPIAgent

from central_node.control_layer.controller_module import *
from central_node.control_layer.scheduler_module.scheduler import Scheduler, EdgeNodeInfo, UserNodeInfo, Latency
from central_node.control_layer.agents_module.scheduler_agent import SchedulerAgent
from central_node.control_layer.agents_module.users_agent import UsersAgent
from central_node.control_layer.prediction_module.prediction import WorkloadPredictor
from central_node.control_layer.helper_module.data_manager import DataManager

from config import Config


class CentralCoreController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize control layer components
        self.scheduler = Scheduler()
        self.predictor = WorkloadPredictor()
        self.data_manager = DataManager()
        self.central_node_api_controller = CentralNodeAPIController()
        self.simulation = False
        self.step_id = None
        self.current_dataset = None
        
        CentralNodeAPIAgent(self.central_node_api_controller).start_all_tasks()
        SchedulerAgent(self.scheduler).start_all_tasks()
        UsersAgent(self.scheduler).start_all_tasks()

    def register_edge_node(self, request_data):
        controller = RegisterEdgeNodeController(self.scheduler, request_data)
        controller.execute()
        return f"Node {request_data.get('node_id')} registered successfully"

    def update_node_metrics(self, node_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        controller = UpdateNodeMetricsController(self.scheduler, node_id, request_data)
        controller.execute()
        return f"Update metrics for node {node_id} updated successfully"
            
    def get_cluster_status(self):
        controller = GetClusterStatusController(self.scheduler, self.central_node_api_controller)
        return controller.execute()
            
    def update_edge_node(self, request_data):
        controler = UpdateEdgeNodeController(self.scheduler, request_data)
        controler.execute()
        return f"Edge node {request_data.get('node_id')} updated successfully"
    
    def create_user_node(self, request_data):
        controller = CreateUserNodeController(self.scheduler, request_data)
        controller.execute()
        return f"User node {request_data.get('user_id')} created successfully"
    
    def update_user_node(self, request_data):
        controller = UpdateUserNodeController(self.scheduler, request_data)
        controller.execute()
        return f"User node {request_data.get('user_id')} updated successfully"

    def get_all_users(self):
        """Get all user nodes"""
        try:
            users = []
            if self.current_dataset == "dact":
                self._update_dact_sample()
            elif self.current_dataset == "vehicles":
                self._update_vehicles_sample()
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
            
    def get_dact_sample(self):
        try:
            sample = self.data_manager.get_dact_data_by_step(659)
            self.step_id = 659
            self.current_dataset = "dact"
            self.scheduler.user_nodes.clear()
            for item in sample.get("items", []):
                user_node = None
                if item.get(f"user_{item.get('id', 0)}") in self.scheduler.user_nodes:
                    user_node = self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")]
                else:
                    location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                    nearest_node_id, nearest_distance = self.scheduler._node_assignment(location)
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
                        user_id=f"user_{item.get('id', 0)}",
                        assigned_node_id=nearest_node_id,
                        location=location,
                        last_executed=0,
                        size=item.get("size", 10),
                        speed=item.get("speed", 5),
                        latency=latency
                    )
                    self.scheduler.create_user_node(user_node)
                
            return {
                "success": True,
                "message": "DACT sample retrieved successfully"
            }
        except Exception as e:
            self.logger.error(f"Error getting DACT sample: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def _update_dact_sample(self):
        if not self.simulation or not self.step_id:
            return False
        
        sample = self.data_manager.get_dact_data_by_step(self.step_id)

        if not sample:
            return False
        
        for item in sample.get("items", []):
            user_node = None
            if item.get(f"user_{item.get('id', 0)}") in self.scheduler.user_nodes:
                user_node = self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")]
                user_node.location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                nearest_node_id, nearest_distance = self.scheduler._node_assignment(user_node.location)
                user_node.assigned_node_id = nearest_node_id
                user_node.latency.propagation_delay = nearest_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000  # Convert to ms
                user_node.latency.total_turnaround_time = user_node.latency.propagation_delay + user_node.latency.transmission_delay
                self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")] = user_node
            else:
                location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                nearest_node_id, nearest_distance = self.scheduler._node_assignment(location)
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
                    user_id=f"user_{item.get('id', 0)}",
                    assigned_node_id=nearest_node_id,
                    location=location,
                    last_executed=0,
                    size=item.get("size", 10),
                    speed=item.get("speed", 5),
                    latency=latency
                )
                self.scheduler.create_user_node(user_node)
        self.step_id += 1
        return True

    def get_vehicles_sample(self):
        try:
            sample = self.data_manager.get_vehicle_data_by_timestep(28800.00)
            self.step_id = 28800.00
            self.current_dataset = "vehicles"
            users = []
            self.scheduler.user_nodes.clear()  # Clear existing users for fresh start
            for item in sample.get("items", []):
                user_node = None
                if item.get(f"user_{item.get('id', 0)}") in self.scheduler.user_nodes:
                    user_node = self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")]
                else:
                    location =  {'x': item.get('x', 0), 'y': item.get('y', 0)}
                    nearest_node_id, nearest_distance = self.scheduler._node_assignment(location)
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
                        user_id=f"user_{item.get('id', 0)}",
                        assigned_node_id=nearest_node_id,
                        location=location,
                        last_executed=0,
                        size=item.get("size", 10),
                        speed=item.get("speed", 5),
                        latency=latency
                    )
                    self.scheduler.create_user_node(user_node)
                users.append({
                    "user_id": user_node.user_id,
                    "assigned_node_id": user_node.assigned_node_id,
                    "location": user_node.location,
                    "last_executed": time.time() - user_node.last_executed,
                    "size": user_node.size,
                    "speed": user_node.speed,
                    "latency": user_node.latency
                })
            return {
                "success": True,
                "total_count": len(users)
            }
        except Exception as e:
            self.logger.error(f"Error getting vehicles sample: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _update_vehicles_sample(self):
        if not self.simulation or not self.step_id:
            return False
        
        sample = self.data_manager.get_vehicle_data_by_timestep(self.step_id)

        if not sample:
            return False
        
        for item in sample.get("items", []):
            user_node = None
            if item.get(f"user_{item.get('id', 0)}") in self.scheduler.user_nodes:
                user_node = self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")]
                user_node.location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                nearest_node_id, nearest_distance = self.scheduler._node_assignment(user_node.location)
                user_node.assigned_node_id = nearest_node_id
                user_node.latency.propagation_delay = nearest_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000  # Convert to ms
                user_node.latency.total_turnaround_time = user_node.latency.propagation_delay + user_node.latency.transmission_delay
                self.scheduler.user_nodes[item.get(f"user_{item.get('id', 0)}")] = user_node
            else:
                location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                nearest_node_id, nearest_distance = self.scheduler._node_assignment(location)
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
                    user_id=f"user_{item.get('id', 0)}",
                    assigned_node_id=nearest_node_id,
                    location=location,
                    last_executed=0,
                    size=item.get("size", 10),
                    speed=item.get("speed", 5),
                    latency=latency
                )
                self.scheduler.create_user_node(user_node)
        self.step_id += 1
        return True

    def start_simulation(self):
        try:
            self.simulation = True
            return {
                "success": True,
                "message": "Simulation started successfully"
            }
        except Exception as e:
            self.logger.error(f"Error starting simulation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def stop_simulation(self):
        try:
            self.simulation = False
            return {
                "success": True,
                "message": "Simulation stopped successfully"
            }
        except Exception as e:
            self.logger.error(f"Error stopping simulation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def set_scheduling_strategy(self, strategy_name: str):
        """Set the scheduling strategy"""
        try:
            from central_node.control_layer.scheduler_module.scheduler import SchedulingStrategy
            
            # Map string to enum
            strategy_map = {
                'round_robin': SchedulingStrategy.ROUND_ROBIN,
                'least_loaded': SchedulingStrategy.LEAST_LOADED,
                'geographic': SchedulingStrategy.GEOGRAPHIC,
                'predictive': SchedulingStrategy.PREDICTIVE,
                'gap_baseline': SchedulingStrategy.GAP_BASELINE
            }
            
            if strategy_name not in strategy_map:
                return {
                    "success": False,
                    "error": f"Unknown strategy: {strategy_name}. Available: {list(strategy_map.keys())}"
                }
            
            self.scheduler.set_scheduling_strategy(strategy_map[strategy_name])
            
            return {
                "success": True,
                "message": f"Scheduling strategy set to: {strategy_name}",
                "strategy": strategy_name
            }
            
        except Exception as e:
            self.logger.error(f"Error setting scheduling strategy: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_scheduling_strategy(self):
        """Get current scheduling strategy"""
        try:
            current_strategy = self.scheduler.get_scheduling_strategy()
            return {
                "success": True,
                "strategy": current_strategy,
                "available_strategies": [
                    "round_robin", "least_loaded", "geographic", 
                    "predictive", "gap_baseline"
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting scheduling strategy: {e}")
            return {
                "success": False,
                "error": str(e)
            }