from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config

class SetDatasetController:
    def __init__(self, scheduler: Scheduler, data_manager: DataManager, request_data: dict):
        self.scheduler = scheduler
        self.data_manager = data_manager
        self.request_data = request_data
        self.dataset_name = self.request_data.get("dataset_name")
        self.sample_size = self.request_data.get("sample_size", None)
        self.scheduler.clear_all_users()
        self._validate()

    def _validate(self):
        if self.dataset_name not in ["none", "dact", "random_generated"]:
            raise ValueError(f"Dataset {self.dataset_name} is not available.")

        if self.sample_size is not None and (not isinstance(self.sample_size, int) or self.sample_size <= 0 or self.sample_size > 1000):
            raise ValueError("Sample size must be a positive integer not exceeding 1000.")
        
    def start_sample_data(self):
        sample_data = {}
        if self.dataset_name == "dact":
            self.scheduler.current_step_id = 659
            sample_data = self.data_manager.get_dact_data_by_step(self.scheduler.current_step_id)
        elif self.dataset_name == "random_generated":
            self.scheduler.current_step_id = 1
            self.scheduler.set_random_sample_size(self.sample_size)
            sample_data = self.data_manager.get_random_generated_data(self.scheduler.current_step_id, self.sample_size)

        for item in sample_data.get("items", []):
            user_id = item.get("id")  # Unified access to user ID
            if user_id in self.scheduler.user_nodes:
                user_node = self.scheduler.user_nodes[user_id]
            else:
                # Unified access to location keys
                location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
                bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
                transmission_delay = data_size / bandwidth
                total_turnaround_time = transmission_delay
                latency = Latency(
                    distance=0,
                    data_size=data_size,
                    bandwidth=bandwidth,
                    propagation_delay=0.0,
                    transmission_delay=transmission_delay,
                    computation_delay=0.0,
                    container_status="unknown",
                    total_turnaround_time=total_turnaround_time
                )
                user_node = UserNodeInfo(
                    user_id=f"user_{user_id}",
                    assigned_node_id=None,
                    location=location,
                    last_executed=0,
                    size=item.get("size", 10),  # Default size if not provided
                    speed=item.get("speed", 5),  # Default speed if not provided
                    latency=latency
                )
                self.scheduler.create_user_node(user_node)

        self.scheduler.node_assignment()
                
    def execute(self):
        if self.dataset_name == "none":
            self.scheduler.clear_all_users()
            return "Dataset cleared successfully"
        if self.dataset_name == "random_generated" and self.sample_size is not None:
            self.scheduler.set_random_sample_size(self.sample_size)

        self.start_sample_data()
        return f"Dataset set to {self.dataset_name} successfully"