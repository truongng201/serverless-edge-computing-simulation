"""
Edge Node API Layer
Handles container execution requests and reports metrics to central node
"""

import logging
import time
import threading
import random
import string
from typing import Dict, Any, Optional
import requests

from shared_resource_layer.container_manager import ContainerManager, ContainerState
from shared_resource_layer.system_metrics import SystemMetricsCollector
from config import Config


class EdgeNodeAPI:
    def __init__(self, node_id: str, central_node_url: str):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.central_node_url = central_node_url
        
        # Initialize managers
        self.container_manager = ContainerManager()
        self.metrics_collector = SystemMetricsCollector()
        
        # Metrics reporting
        self.metrics_thread = None
        self.is_reporting = False
        self.reporting_interval = Config.METRICS_COLLECTION_INTERVAL
        
        # Request tracking
        self.active_requests = 0
        self.total_requests = 0
        self.response_times = []
        
        # Cleanup idle containers
        self.cleanup_thread = None
        self.is_cleaning = False
        self.cleanup_interval = Config.CLEANUP_IDLE_CONTAINERS_INTERVAL
        
        self.logger.info(f"Edge Node API initialized: {node_id}")
        
    def start_metrics_reporting(self):
        """Start reporting metrics to central node"""
        if self.is_reporting:
            return
            
        self.is_reporting = True
        self.metrics_thread = threading.Thread(target=self._metrics_reporting_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        
        # Register with central node
        self._register_with_central_node()
        
        self.logger.info("Metrics reporting started")
        
    def stop_metrics_reporting(self):
        """Stop metrics reporting"""
        self.is_reporting = False
        if self.metrics_thread:
            self.metrics_thread.join()
        self.logger.info("Metrics reporting stopped")
        
    def _register_with_central_node(self):
        """Register this edge node with the central node"""
        try:
            registration_data = {
                "node_id": self.node_id,
                "endpoint": f"http://localhost:{self._get_port()}",
                "location": {"lat": 0.0, "lng": 0.0},  # TODO: Get actual location
                "resources": self._get_node_resources()
            }
            
            response = requests.post(
                f"{self.central_node_url}/api/v1/central/nodes/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Successfully registered with central node")
            else:
                self.logger.error(f"Failed to register with central node: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Registration failed: {e}")
            
    def _get_port(self) -> int:
        """Get the port this edge node is running on"""
        # TODO: Get actual port from Flask app
        return 5002  # Default edge node port
        
    def _get_node_resources(self) -> Dict[str, Any]:
        """Get node resource information"""
        docker_info = self.container_manager.get_docker_info()
        return {
            "memory_total": docker_info.get("memory_total", 0) if docker_info else 0,
            "cpus": docker_info.get("cpus", 1) if docker_info else 1,
            "containers_max": 10  # Configurable limit
        }
        
    def _metrics_reporting_loop(self):
        """Main metrics reporting loop"""
        while self.is_reporting:
            try:
                metrics = self._collect_node_metrics()
                if metrics:
                    self._send_metrics_to_central(metrics)
                    
                time.sleep(self.reporting_interval)
                
            except Exception as e:
                self.logger.error(f"Error in metrics reporting loop: {e}")
                time.sleep(self.reporting_interval)
                
    def _collect_node_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect comprehensive node metrics"""
        try:
            system_metrics = self.metrics_collector.get_detailed_metrics()
            if not system_metrics:
                return None
                
            # Get container information
            containers = self.container_manager.list_containers()
            running_containers = len([c for c in containers if c.state == ContainerState.RUNNING])
            warm_containers = len([c for c in containers if c.state == ContainerState.IDLE])
            
            # Calculate average response time
            avg_response_time = 0.0
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                # Keep only recent response times (last 100)
                self.response_times = self.response_times[-100:]
                
            return {
                "cpu_usage": system_metrics["cpu_usage"],
                "memory_usage": system_metrics["memory_usage"],
                "running_container": running_containers,
                "warm_container": warm_containers,
                "active_requests": self.active_requests,
                "total_requests": self.total_requests,
                "response_time_avg": avg_response_time,
                "energy_consumption": system_metrics["cpu_energy_kwh"],
                "load_average": system_metrics["load_average"],
                "uptime": system_metrics["uptime"],
                "timestamp": system_metrics["timestamp"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect node metrics: {e}")
            return None
            
    def _send_metrics_to_central(self, metrics: Dict[str, Any]):
        """Send metrics to central node"""
        try:
            response = requests.post(
                f"{self.central_node_url}/api/v1/central/nodes/{self.node_id}/metrics",
                json=metrics,
                timeout=5
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to send metrics: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to send metrics to central node: {e}")
            
    def execute_function(self, function_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a serverless function"""
        start_time = time.time()
        self.active_requests += 1
        self.total_requests += 1
        
        try:
            random_string_name = ''.join(random.choices(string.ascii_letters + string.digits, k=Config.DEFAULT_CONTAINER_ID_LENGTH))
            image = function_data.get("image", Config.DEFAULT_CONTAINER_IMAGE)
            function_data["function_name"] = f"fn_{random_string_name}"
            function_data["image"] = image

            # Check if we need to create a new container or reuse existing
            container_id = self._get_or_create_container(function_data["function_name"], image)

            if not container_id:
                return {
                    "success": False,
                    "error": "Failed to create or reuse container",
                    "execution_time": time.time() - start_time
                }

            execution_time = time.time() - start_time
            self.response_times.append(execution_time)
            result = self.container_manager.execute_container(container_id, function_data)
            
            if not self.container_manager.idle_container(container_id):
                return {
                    "success": False,
                    "error": "Failed to create or reuse container",
                    "execution_time": time.time() - start_time
                }

            return {
                "success": True,
                "result": result,
                "function_name": function_data["function_name"],
                "container_id": container_id,
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
            
    def _get_or_create_container(self, function_name: str, image: str) -> Optional[str]:
        """Get existing container or create new one"""
        # Check for existing idle container for this function
        containers = self.container_manager.list_containers(ContainerState.IDLE)
        for container in containers:
            # Reuse existing container (warm start)
            if time.time() - container.stopped_at > Config.DEFAULT_MAX_IDLE_TIME:
                continue

            if self.container_manager.start_container(container.container_id):
                self.logger.info(f"Warm start for function {function_name}")
                return container.container_id

        # Create new container (cold start)
        container_id = self.container_manager.create_container(
            name=function_name,
            image=image,
        )

        if container_id and self.container_manager.start_container(container_id):
            self.logger.info(f"Cold start for function {function_name}")
            return container_id
        return None

    def _cleanup_idle_containers(self, max_idle_time: int = Config.DEFAULT_MAX_IDLE_TIME) -> None:
        """Clean up containers that have been idle too long"""
        current_time = time.time()
        idle_containers = self.container_manager.list_containers(ContainerState.IDLE)
        
        for container in idle_containers:
            if container.stopped_at and (current_time - container.stopped_at) > max_idle_time:
                self.container_manager.remove_container(container.container_id)
                self.logger.info(f"Cleaned up idle container: {container.container_id[:12]}")
   
    def cleanup_idle_containers_loop(self):
        """Periodically clean up idle containers"""
        while True:
            try:
                self._cleanup_idle_containers()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.cleanup_interval)

    def start_cleanup_containers(self):
        """Start cleanup unused containers"""
        if self.is_cleaning:
            return
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_idle_containers_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
    def stop_cleanup_containers(self):
        """Stop cleanup unused containers"""
        self.is_cleaning = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        self.logger.info("Cleanup thread stopped")

    def get_node_status(self) -> Dict[str, Any]:
        """Get current node status"""
        system_metrics = self.metrics_collector.collect_metrics()
        containers = self.container_manager.list_containers()
        
        container_states = {}
        for state in ContainerState:
            container_states[state.value] = len([c for c in containers if c.state == state])
            
        return {
            "node_id": self.node_id,
            "status": "running",
            "cpu_usage": system_metrics.cpu_usage if system_metrics else 0,
            "memory_usage": system_metrics.memory_usage if system_metrics else 0,
            "containers": container_states,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "uptime": system_metrics.uptime if system_metrics else 0,
            "timestamp": time.time()
        }

