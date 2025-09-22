import random
import time

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config

class StartDactSampleController:
    def __init__(self, data_manager: DataManager, scheduler: Scheduler):
        self.data_manager = data_manager
        self.scheduler = scheduler
        self.current_step_id = 659
        self.current_dataset = "dact"
        self.scheduler.user_nodes.clear()
        
    def _update_scheduler(self):
        self.scheduler.current_dataset = self.current_dataset
        self.scheduler.current_step_id = self.current_step_id

    def _get_dact_sample(self):
        sample = self.data_manager.get_dact_data_by_step(self.current_step_id)

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
                    latency=latency,
                    created_at=time.time(),
                    last_updated=time.time()
                )
                self.scheduler.create_user_node(user_node)

    def execute(self):
        self._update_scheduler()
        self._get_dact_sample()

