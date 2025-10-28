import random
import time

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config

class StartRandomGeneratedSampleController:
    def __init__(self, data_manager: DataManager, scheduler: Scheduler):
        self.data_manager = data_manager
        self.scheduler = scheduler
        self.current_step_id = 1
        self.current_dataset = "random_generated"
        self.scheduler.user_nodes.clear()
        
    def _update_scheduler(self):
        self.scheduler.current_dataset = self.current_dataset
        self.scheduler.current_step_id = self.current_step_id

    def _get_random_generated_sample(self):
        # Get random generated data from data manager
        sample_data = self.data_manager.get_random_generated_data(self.current_step_id)

        for item in sample_data:
            user_id = f"user_{item.get('user_id', 0)}"
            user_node = None
            
            if user_id in self.scheduler.user_nodes:
                user_node = self.scheduler.user_nodes[user_id]
            else:
                location = {'x': item.get('location_x', 0), 'y': item.get('location_y', 0)}
                
                # Use default configuration values for data size and bandwidth
                data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
                bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
                propagation_delay = 0 / Config.DEFAULT_PROPAGATION_SPEED_IN_METERS * 1000  # Convert to ms
                transmission_delay = data_size / bandwidth
                total_turnaround_time = propagation_delay + transmission_delay
                
                latency = Latency(
                    distance=0,
                    data_size=data_size,
                    bandwidth=bandwidth,
                    propagation_delay=propagation_delay,
                    transmission_delay=transmission_delay,
                    computation_delay=0.0,
                    container_status="unknown",
                    total_turnaround_time=total_turnaround_time
                )
                
                user_node = UserNodeInfo(
                    user_id=user_id,
                    assigned_node_id=None,
                    location=location,
                    last_executed=0,
                    size=5,
                    speed=5,
                    latency=latency
                )
                
                self.scheduler.create_user_node(user_node)
        self.scheduler.node_assignment()

    def execute(self):
        self._update_scheduler()
        self._get_random_generated_sample()