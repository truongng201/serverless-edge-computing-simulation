import random
import time

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config
from shared import InvalidDataException


class CreateUserNodeController:
    def __init__(self, scheduler: Scheduler, user_data: dict):
        self.scheduler = scheduler
        self.user_data = user_data
        self._validate_user_data()

    def _validate_user_data(self):
        if not self.user_data or "user_id" not in self.user_data:
            raise InvalidDataException("Invalid user data")

    def _create_user_node(self):
        user_location = self.user_data.get("location", {"x": 0.0, "y": 0.0})
        # Compute assignment for this single user location using greedy rule
        assigned_node_id, assigned_node_distance = self.scheduler._greedy_assignment(user_location)
        # data_size = random.randint(*Config.DEFAULT_RANDOM_DATA_SIZE_RANGE_IN_BYTES)
        # bandwidth = random.randint(*Config.DEFAULT_RANDOM_BANDWIDTH_RANGE_IN_BYTES_PER_MILLISECOND)
        data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
        bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
        propagation_delay = assigned_node_distance / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000  # Convert to ms
        transmission_delay = data_size / bandwidth
        total_turnaround_time = propagation_delay + transmission_delay
        
        latency = Latency(
            distance=assigned_node_distance,
            data_size=data_size,
            bandwidth=bandwidth,
            propagation_delay=propagation_delay,
            transmission_delay=transmission_delay,
            computation_delay=0.0,
            container_status="unknown",
            total_turnaround_time=total_turnaround_time
        )
        
        user_node = UserNodeInfo(
            user_id=self.user_data.get("user_id"),
            assigned_node_id=assigned_node_id,
            location=user_location,
            last_executed=0,
            size=self.user_data.get("size", 10),
            speed=self.user_data.get("speed", 5),
            latency=latency,
            # Add optimization parameters
            bandwidth_demand=bandwidth,
            memory_demand=Config.DEFAULT_USER_MEMORY_DEMAND,
            data_size_demand=data_size,
            previous_node_id=None,
            migration_cost=0.0,
            cold_start_penalty=0.0
        )
        self.scheduler.create_user_node(user_node)
        # Update assignment matrix entry for this user (optional)
        try:
            self.scheduler.assignment_matrix[user_node.user_id] = (assigned_node_id, assigned_node_distance)
        except Exception:
            pass

    def execute(self):
        self._create_user_node()
