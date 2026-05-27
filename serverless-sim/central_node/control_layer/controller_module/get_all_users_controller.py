import random
import time
import requests

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager
from central_node.control_layer.models import Latency, UserNodeInfo

from config import Config

class GetAllUsersController:
    def __init__(self, scheduler: Scheduler, data_manager: DataManager):
        self.scheduler = scheduler
        self.data_manager = data_manager
        self.current_step_id = self.scheduler.get_current_step_id()
        self.current_dataset = self.scheduler.get_current_dataset()
        self.random_sample_size = self.scheduler.get_sample_size()
        self.simulation = self.scheduler.simulation
        self.response = []
        self.execution_stats = None
       
    def _update_scheduler(self):
        self.scheduler.set_current_dataset(self.current_dataset)
        self.scheduler.set_current_step_id(self.current_step_id)
        
    def _update_dact_sample(self):
        if not self.simulation or not self.current_step_id:
            return False
        
        sample = self.data_manager.get_dact_data_by_step(self.current_step_id)

        if not sample:
            # If we hit the end of dataset, wrap to the beginning for continuous playback
            self.current_step_id = 1
            sample = self.data_manager.get_dact_data_by_step(self.current_step_id)
            if not sample:
                return False
        
        for item in sample.get("items", []):
            user_id = f"user_{item.get('id', 0)}"
            location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
            if user_id in self.scheduler.user_nodes:
                # Update existing user via scheduler helper (updates last_updated & history)
                self.scheduler.update_user_node(user_id, location)
                user_node = self.scheduler.user_nodes[user_id]
                # Keep speed/size in sync if present
                user_node.size = item.get("size", user_node.size)
                user_node.speed = item.get("speed", user_node.speed)
                # Refresh propagation delay and total time with updated distance
                dist_m = getattr(user_node.latency, 'distance', 0)
                user_node.latency.propagation_delay = self.scheduler._calculate_propagation_delay(dist_m)
                user_node.latency.total_turnaround_time = (
                    user_node.latency.propagation_delay
                    + getattr(user_node.latency, 'transmission_delay', 0)
                    + getattr(user_node.latency, 'computation_delay', 0)
                )
            else:
                location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
                data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
                bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
                transmission_delay = data_size / bandwidth
                total_turnaround_time = 0 + transmission_delay
                latency = Latency(
                    distance=0,
                    data_size=data_size,
                    bandwidth=bandwidth,
                    propagation_delay=0,
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
                    size=item.get("size", 10),
                    speed=item.get("speed", 5),
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
        self.current_step_id += 1
        return True
    
    def _update_random_generated_sample(self):
        if not self.simulation or not self.current_step_id:
            return False
        
        sample_data = self.data_manager.get_random_generated_data(self.current_step_id, self.random_sample_size)

        if not sample_data:
            # If no data, wrap back to the beginning for continuous playback
            self.current_step_id = 1
            sample_data = self.data_manager.get_random_generated_data(self.current_step_id, self.random_sample_size)
            if not sample_data:
                return False

        for item in sample_data.get("items", []):
            user_id = f"user_{item.get('id', 0)}"
            location = {'x': item.get('x', 0), 'y': item.get('y', 0)}
            if user_id in self.scheduler.user_nodes:
                # Update existing user via scheduler helper (updates last_updated & history)
                self.scheduler.update_user_node(user_id, location)
                user_node = self.scheduler.user_nodes[user_id]
                # Refresh propagation delay and total time with updated distance
                dist_m = getattr(user_node.latency, 'distance', 0)
                user_node.latency.propagation_delay = self.scheduler._calculate_propagation_delay(dist_m)
                user_node.latency.total_turnaround_time = (
                    user_node.latency.propagation_delay
                    + getattr(user_node.latency, 'transmission_delay', 0)
                    + getattr(user_node.latency, 'computation_delay', 0)
                )
            else:
                data_size = Config.DEFAULT_DATA_SIZE_IN_BYTES
                bandwidth = Config.DEFAULT_BANDWIDTH_IN_BYTES_PER_MILLISECOND
                transmission_delay = data_size / bandwidth
                total_turnaround_time = transmission_delay
                
                latency = Latency(
                    distance=0,
                    data_size=data_size,
                    bandwidth=bandwidth,
                    propagation_delay=0,
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
                    size=random.randint(5, 15),  # Random size between 5-15
                    speed=random.randint(3, 8),  # Random speed between 3-8
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
        
        self.current_step_id += 1
        return True

    def _update_taxid_replay_sample(self):
        """
        Advance all TaxiD replay users by one step along their preloaded trajectories.

        Trajectories are stored on scheduler as:
          trajectories_px: {user_id: [{"ts": ..., "x": float, "y": float, ...}, ...]}
          
        If features (v, a, delta_v, etc.) are included in trajectory points,
        they will be used directly instead of being recomputed.
        """
        if not self.simulation:
            return False
       
        trajectories_px = self.scheduler.get_trajectories_px()
        step = self.scheduler.get_current_step_id()
        if not trajectories_px:
            print("No trajectories found for TaxiD replay.")
            return False
        
        max_len = 0
        for user_id, seq in trajectories_px.items():
            if not seq:
                print(f"No seq for {user_id}")
                continue
            max_len = max(max_len, len(seq))
            idx = min(step, len(seq) - 1)
            pt = seq[idx]
            
            if user_id in self.scheduler.user_nodes:
                # Use update_user_node_with_features if features are available
                # This automatically falls back to computing features if not present
                self.scheduler.update_user_node_with_features(user_id, pt)
                
                user_node = self.scheduler.user_nodes[user_id]
                dist_m = getattr(user_node.latency, "distance", 0.0)
                user_node.latency.propagation_delay = self.scheduler._calculate_propagation_delay(dist_m)
                user_node.latency.total_turnaround_time = (
                    user_node.latency.propagation_delay
                    + getattr(user_node.latency, "transmission_delay", 0.0)
                    + getattr(user_node.latency, "computation_delay", 0.0)
                )
        
        if max_len == 0:
            return False
        self.current_step_id = min(step + 1, max_len - 1) 
        return True

    def _get_all_users(self):
        self.response = []
        dataset = self.current_dataset
        dataset_name = dataset.get("name") if isinstance(dataset, dict) else dataset

        if dataset_name == "dact":
            self._update_dact_sample()
        elif dataset_name == "random_generated":
            self._update_random_generated_sample()
            self.scheduler.node_assignment()
        elif dataset_name == "taxiD_Replay":
            self._update_taxid_replay_sample()
            # Keep scheduler step in sync so predictive planning uses the correct timestep.
            self.scheduler.set_current_step_id(self.current_step_id)
            self.scheduler.node_assignment()
        
        # Execute functions at this timestep if simulation is active and users_agent is available
        if self.simulation and self.scheduler.user_nodes and self.current_step_id % 5 == 0:
            self._execute_function()
        
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
            
    def _execute_function(self):
        # NOTE: In large experiments, real /execute calls can dominate runtime.
        # `EXECUTION_MODE=simulated` avoids network/Docker and assigns computation_delay analytically.
        if getattr(Config, "EXECUTION_MODE", "real") == "simulated":
            step_id = self.current_step_id or 0
            for _, user_node in self.scheduler.user_nodes.items():
                assigned_node = user_node.assigned_node_id
                if not assigned_node:
                    continue
                is_edge = assigned_node != "central_node"

                warm_ms = Config.SIM_EXEC_WARM_MS_EDGE if is_edge else Config.SIM_EXEC_WARM_MS_CENTRAL
                cold_penalty_ms = (
                    Config.SIM_EXEC_COLD_PENALTY_MS_EDGE if is_edge else Config.SIM_EXEC_COLD_PENALTY_MS_CENTRAL
                )

                # Consider node warm if:
                # - user executed on the same node previously, OR
                # - predictive prewarm-only has planned this node for the current step
                algorithm = str(self.scheduler.get_assignment_algorithm() or "")
                warm = user_node.last_executed_node_id == assigned_node
                if algorithm == "prediction without warm-state-awareness":
                    warm = False
                elif getattr(Config, "PREDICTIVE_PREWARM_ONLY", False):
                    if user_node.planned_node_id == assigned_node and user_node.planned_step_id == step_id:
                        warm = True

                user_node.latency.computation_delay = warm_ms if warm else (warm_ms + cold_penalty_ms)
                user_node.latency.container_status = "warm" if warm else "cold"
                user_node.last_executed = time.time()
                user_node.last_executed_node_id = assigned_node
                user_node.last_executed_step_id = step_id
            return

        # Real execution (Docker-backed) via HTTP
        for _, user_node in self.scheduler.user_nodes.items():
            assigned_node = user_node.assigned_node_id
            if not assigned_node:
                continue
            central_node = self.scheduler.central_node
            if central_node["node_id"] == assigned_node:
                try:
                    url = f"http://{central_node['endpoint']}/api/v1/central/execute"
                    result = requests.Session().post(
                        url,
                        json={"user_id": user_node.user_id},
                        timeout=10
                    )
                    
                    if result.status_code == 200:
                        data = result.json().get("data", {})
                        user_node.latency.computation_delay = data.get("execution_time", 0.0) * 1000
                        user_node.latency.container_status = data.get("container_status", "unknown")
                        user_node.last_executed = time.time()
                        
                except Exception:
                    continue
            
            edge_node = self.scheduler.edge_nodes.get(assigned_node)
            if edge_node:
                try:
                    url = f"http://{edge_node.endpoint}/api/v1/edge/execute"
                    
                    result = requests.Session().post(
                        url,
                        json={"user_id": user_node.user_id},
                        timeout=10
                    )
                    
                    if result.status_code == 200:
                        data = result.json()
                        user_node.latency.computation_delay = data.get("execution_time", 0.0) * 1000
                        user_node.latency.container_status = data.get("container_status", "unknown")
                        user_node.last_executed = time.time()
                except Exception:
                    continue


    def execute(self):
        self._get_all_users()
        self._update_scheduler()
        return self.response
