import random
import time

from central_node.control_layer.scheduler_module.scheduler import Scheduler, Latency, UserNodeInfo
from central_node.control_layer.helper_module.data_manager import DataManager

from config import Config

class GetAllUsersController:
    def __init__(self, scheduler: Scheduler, data_manager: DataManager):
        self.scheduler = scheduler
        self.data_manager = data_manager
        self.current_step_id = self.scheduler.current_step_id
        self.current_dataset = self.scheduler.current_dataset
        self.simulation = self.scheduler.simulation
        self.response = []
       
    def _update_scheduler(self):
        self.scheduler.current_dataset = self.current_dataset
        self.scheduler.current_step_id = self.current_step_id
        
    def _update_dact_sample(self):
        if not self.simulation or not self.current_step_id:
            return False
        
        sample = self.data_manager.get_dact_data_by_step(self.current_step_id)

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
        self.current_step_id += 1
        return True
    
    
    def _update_vehicles_sample(self):
        if not self.simulation or not self.current_step_id:
            return False
        
        sample = self.data_manager.get_vehicle_data_by_timestep(self.current_step_id)

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
        self.current_step_id += 1
        return True
       
        
    def _get_all_users(self):
        self.response = []
        if self.current_dataset == "dact":
            self._update_dact_sample()
        elif self.current_dataset == "vehicles":
            self._update_vehicles_sample()
        for user_id, user_node in self.scheduler.user_nodes.items():
            assigned_edge = None
            assigned_central = None
            
            if user_node.assigned_node_id == "central_node":
                assigned_central = "central_node"
            elif user_node.assigned_node_id in self.scheduler.edge_nodes:
                assigned_edge = user_node.assigned_node_id
            user_node.latency.total_turnaround_time = user_node.latency.propagation_delay + user_node.latency.transmission_delay + user_node.latency.computation_delay
            self.response.append({
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


    def execute(self):
        self._get_all_users()
        self._update_scheduler()
        return self.response