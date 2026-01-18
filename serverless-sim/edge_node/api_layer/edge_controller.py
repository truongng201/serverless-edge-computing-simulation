import logging
import time
import random
import string
from typing import Dict, Any, Tuple
import re

from shared.resource_layer import ContainerManager, SystemMetricsCollector
from config import Config, ContainerState


_SAFE_CONTAINER_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe_name(value: str) -> str:
    value = _SAFE_CONTAINER_NAME_RE.sub("_", value).strip("_.-")
    return value or "anon"


def _function_name_for_request(function_data: Dict[str, Any]) -> str:
    if not Config.STICKY_FUNCTION_PER_USER:
        random_string_name = "".join(
            random.choices(string.ascii_letters + string.digits, k=Config.DEFAULT_CONTAINER_ID_LENGTH)
        )
        return f"fn_{random_string_name}"

    user_id = str(function_data.get("user_id", "unknown"))
    base = _safe_name(user_id)
    if getattr(Config, "FUNCTION_NAME_BUCKETS", 0) and Config.FUNCTION_NAME_BUCKETS > 0:
        bucket = abs(hash(user_id)) % int(Config.FUNCTION_NAME_BUCKETS)
        return f"fn_bucket_{bucket:04d}"
    return f"fn_user_{base}"


class EdgeNodeAPIController:
    def __init__(self, node_id: str, central_node_url: str):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.central_node_url = central_node_url

        # Initialize managers
        self.container_manager = ContainerManager()
        self.metrics_collector = SystemMetricsCollector()
        
        # Request tracking
        self.active_requests = 0
        self.total_requests = 0
        self.response_times = []
        
        self.logger.info(f"Edge Node API Controller initialized: {node_id}")
    
    def get_request_tracking(self):
        return {
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "response_times": self.response_times
        }
        
    
    def execute_function(self, function_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a serverless function"""
        start_time = time.time()
        self.active_requests += 1
        self.total_requests += 1
        
        try:
            image = function_data.get("image", Config.DEFAULT_CONTAINER_IMAGE)
            function_data["function_name"] = _function_name_for_request(function_data)
            function_data["image"] = image

            # Check if we need to create a new container or reuse existing
            container_id, container_status = self._get_or_create_container(function_data["function_name"], image)

            if not container_id:
                return {
                    "success": False,
                    "error": "Failed to create or reuse container",
                    "execution_time": time.time() - start_time
                }

            result = self.container_manager.execute_container(container_id, function_data)
            execution_time = time.time() - start_time
            self.response_times.append(execution_time)
                
            return {
                "success": True,
                "result": result,
                "function_name": function_data["function_name"],
                "container_id": container_id,
                "container_status": container_status,
                "execution_time": execution_time,
                "node_id": self.node_id
            }
            
        except Exception as e:
            self.logger.error(f"Function execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        finally:
            self.active_requests -= 1
            
    def _get_or_create_container(self, function_name: str, image: str) -> Tuple[str]:
        """Get existing container or create new one"""
        now = time.time()
        warm_containers = self.container_manager.list_containers(ContainerState.WARM)

        if Config.STICKY_FUNCTION_PER_USER:
            for container in warm_containers:
                if container.name != function_name:
                    continue
                if container.started_at and now - container.started_at > Config.DEFAULT_MAX_WARM_TIME:
                    container.state = ContainerState.DEAD
                    self.container_manager.remove_container(container.container_id, force=True)
                    break
                if self.container_manager.restart_container(container.container_id, function_name):
                    self.logger.info(f"Warm start for function {function_name}")
                    return container.container_id, "warm"
        else:
            for container in warm_containers:
                # Reuse existing container (warm start)
                if container.started_at and now - container.started_at > Config.DEFAULT_MAX_WARM_TIME:
                    container.state = ContainerState.DEAD
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

    def get_node_status(self) -> Dict[str, Any]:
        """Get current node status"""
        system_metrics = self.metrics_collector.get_detailed_metrics()
        containers = self.container_manager.list_containers()
        
        container_states = {}
        for state in ContainerState:
            if state.value in ["init", "dead"]:
                continue
            container_states[state.value] = len([c for c in containers if c.state == state])
            
        return {
            "node_id": self.node_id,
            "status": "running",
            "cpu_usage": system_metrics["cpu_usage"] if system_metrics else 0,
            "memory_usage": system_metrics["memory_usage"] if system_metrics else 0,
            "containers": container_states,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "uptime": system_metrics["uptime"] if system_metrics else 0,
            "timestamp": time.time()
        }

