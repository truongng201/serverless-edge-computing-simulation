import logging
import threading
import requests
import time
from typing import Dict, Any

from edge_node.api_layer.edge_controller import EdgeNodeAPIController

from config import Config, ContainerState


class EdgeNodeAPIAgent:
    def __init__(self, node_id: str, central_node_url: str, node_port: int, edge_node_url: str, controller: EdgeNodeAPIController):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.central_node_url = central_node_url
        self.node_port = node_port
        self.edge_node_url = edge_node_url
        self.controller = controller


        # Initialize managers
        self.container_manager = self.controller.container_manager
        self.metrics_collector = self.controller.metrics_collector
        
        # Metrics reporting
        self.metrics_thread = None
        self.is_reporting = False
        self.reporting_interval = Config.METRICS_COLLECTION_INTERVAL
        
        # Cleanup warm containers
        self.cleanup_thread = None
        self.is_cleaning = False
        self.cleanup_interval = Config.CLEANUP_WARM_CONTAINERS_INTERVAL

        self.logger.info(f"Edge Node API Agent initialized: {node_id}")
        
    def start_metrics_reporting(self):
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
        self.is_reporting = False
        if self.metrics_thread:
            self.metrics_thread.join()
        self.logger.info("Metrics reporting stopped")
        
    def _register_with_central_node(self):
        try:
            registration_data = {
                "node_id": self.node_id,
                "endpoint": f"{self.edge_node_url}:{self.node_port}",
                "location": {"x": 300, "y": 200},
                "system_info": self.metrics_collector.get_system_info()
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
                
    def _collect_node_metrics(self):
        try:
            system_metrics = self.metrics_collector.get_detailed_metrics()
            if not system_metrics:
                return None
                
            # Get container information
            containers = self.container_manager.list_containers()
            running_containers = len([c for c in containers if c.state == ContainerState.RUNNING])
            warm_containers = len([c for c in containers if c.state == ContainerState.WARM])

            request_tracking = self.controller.get_request_tracking()
            active_requests = request_tracking["active_requests"]
            total_requests = request_tracking["total_requests"]
            response_times = request_tracking["response_times"]
            # Calculate average response time
            avg_response_time = 0.0
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                response_times = response_times[-100:]  # Keep only recent response times (last 100)

            return {
                "cpu_usage": system_metrics["cpu_usage"],
                "memory_usage": system_metrics["memory_usage"],
                "memory_total": system_metrics["memory_total"],
                "running_container": running_containers,
                "warm_container": warm_containers,
                "active_requests": active_requests,
                "total_requests": total_requests,
                "response_time_avg": avg_response_time,
                "energy_consumption": system_metrics["cpu_energy_kwh"],
                "load_average": system_metrics["load_average"],
                "uptime": system_metrics["uptime"],
                "timestamp": system_metrics["timestamp"],
                "system_info": self.metrics_collector.get_system_info(),
                "endpoint": f"{self.edge_node_url}:{self.node_port}",
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect node metrics: {e}")
            return None
            
    def _send_metrics_to_central(self, metrics: Dict[str, Any]):
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
            
    def _cleanup_warm_containers(self, max_warm_time: int = Config.DEFAULT_MAX_WARM_TIME) -> None:
        current_time = time.time()
        warm_containers = self.container_manager.list_containers(ContainerState.WARM)

        for container in warm_containers:
            if container.stopped_at and (current_time - container.stopped_at) > max_warm_time:
                self.container_manager.remove_container(container.container_id)
                self.logger.info(f"Cleaned up warm container: {container.container_id[:12]}")
   
    def cleanup_warm_containers_loop(self):
        while True:
            try:
                self._cleanup_warm_containers()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.cleanup_interval)

    def start_cleanup_containers(self):
        if self.is_cleaning:
            return
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_warm_containers_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup thread started")
        
    def stop_cleanup_containers(self):
        self.is_cleaning = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        self.logger.info("Cleanup thread stopped")

    def start_all_tasks(self):
        self.start_metrics_reporting()
        self.start_cleanup_containers()

    def end_all_tasks(self):
        self.stop_metrics_reporting()
        self.stop_cleanup_containers()