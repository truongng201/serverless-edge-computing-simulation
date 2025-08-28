import logging
import time
import random
import string
from typing import Dict, Any, Tuple


from shared.resource_layer import ContainerManager, SystemMetricsCollector
from shared import BadRequestException

from config import Config, ContainerState


class CentralNodeAPIController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize control layer components
        self.container_manager = ContainerManager()
        self.metrics_collector = SystemMetricsCollector()
        
        # Request tracking
        self.active_requests = 0
        self.total_requests = 0
        self.response_times = []
        
        self.logger.info("Central Node API Controller initialized")
        
    def get_request_tracking(self):
        return {
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "response_times": self.response_times
        }
        
    def execute_function(self, function_data: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        random_string_name = ''.join(random.choices(string.ascii_letters + string.digits, k=Config.DEFAULT_CONTAINER_ID_LENGTH))
        image = function_data.get("image", Config.DEFAULT_CONTAINER_IMAGE)
        function_data["function_name"] = f"fn_{random_string_name}"
        function_data["image"] = image
        
        container_id, container_status = self._get_or_create_container(function_data["function_name"], image)

        if not container_id:
            raise BadRequestException(f"Failed to create or reuse container {time.time() - start_time}")

        execution_time = time.time() - start_time
        self.response_times.append(execution_time)
        result = self.container_manager.execute_container(container_id, function_data)
        
        if not self.container_manager.warm_container(container_id):
            raise BadRequestException(f"Failed to warm container {container_id}")
        
        self.active_requests += 1
        self.total_requests += 1
        return {
            "status": "success",
            "result": result,
            "function_name": function_data["function_name"],
            "container_id": container_id,
            "container_status": container_status,
            "execution_time": execution_time,
            "node_id": "central_node"
        }
        

    def _get_or_create_container(self, function_name: str, image: str) -> Tuple[str, str]:
        # Check for existing warm container for this function
        containers = self.container_manager.list_containers(ContainerState.WARM)
        for container in containers:
            # Reuse existing container (warm start)
            if time.time() - container.stopped_at > Config.DEFAULT_MAX_WARM_TIME:
                continue

            if self.container_manager.restart_container(container.container_id, function_name):
                self.logger.info(f"Warm start for function {function_name}")
                return container.container_id, "warm"

        # Create new container (cold start)
        container_id = self.container_manager.create_container(
            name=function_name,
            image=image,
        )

        if container_id and self.container_manager.start_container(container_id):
            self.logger.info(f"Cold start for function {function_name}")
            return container_id, "cold"
        return None, None
    
    def get_central_node_status(self) -> Dict[str, Any]:
        system_metrics = self.metrics_collector.collect_metrics()
        containers = self.container_manager.list_containers()
        running_container = len([c for c in containers if c.state == ContainerState.RUNNING])
        warm_container = len([c for c in containers if c.state == ContainerState.WARM])
        return {
            "node_id": "central_node",
            "cpu_usage": system_metrics.cpu_usage if system_metrics else 0,
            "memory_usage": system_metrics.memory_usage if system_metrics else 0,
            "memory_total": system_metrics.memory_total if system_metrics else 0,
            "running_container": running_container,
            "warm_container": warm_container,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "response_time_avg": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "energy_consumption": system_metrics.cpu_energy_kwh if system_metrics else 0,
            "load_average": system_metrics.load_average if system_metrics else [],
            "network_io": {},
            "disk_io": {},
            "timestamp": time.time(),
            "uptime": system_metrics.uptime if system_metrics else 0,
            "system_info": self.metrics_collector.get_system_info() if system_metrics else {}
        }