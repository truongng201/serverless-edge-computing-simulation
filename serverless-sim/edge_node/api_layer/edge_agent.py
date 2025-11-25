import logging
import threading
import requests
import time
from typing import Dict, Any, Optional

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
        """Start metrics reporting thread"""
        if self.is_reporting:
            self.logger.warning("Metrics reporting is already running")
            return
            
        self.is_reporting = True
        self.metrics_thread = threading.Thread(
            target=self._metrics_reporting_loop,
            name=f"EdgeAgent-Metrics-{self.node_id}"
        )
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        
        # Register with central node in a separate thread to not block
        registration_thread = threading.Thread(target=self._register_with_central_node)
        registration_thread.daemon = True
        registration_thread.start()
        
        self.logger.info("Metrics reporting started")
        
    def stop_metrics_reporting(self):
        """Stop metrics reporting thread"""
        self.logger.info("Stopping metrics reporting...")
        self.is_reporting = False
        
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)
            
        self.logger.info("Metrics reporting stopped")
        
    def _register_with_central_node(self):
        """Register this edge node with the central node"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(1, max_retries + 1):
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
                    return
                else:
                    self.logger.error(
                        f"Failed to register with central node: {response.status_code} "
                        f"(attempt {attempt}/{max_retries})"
                    )
                    
            except requests.Timeout:
                self.logger.error(f"Registration timeout (attempt {attempt}/{max_retries})")
            except Exception as e:
                self.logger.error(f"Registration failed (attempt {attempt}/{max_retries}): {e}")
            
            if attempt < max_retries:
                time.sleep(retry_delay)
        
        self.logger.error("Failed to register with central node after all attempts")
            
    def _metrics_reporting_loop(self):
        """Main metrics reporting loop"""
        self.logger.info("Metrics reporting loop started")
        
        while self.is_reporting:
            try:
                loop_start = time.time()
                
                metrics = self._collect_node_metrics()
                if metrics:
                    self._send_metrics_to_central(metrics)
                else:
                    self.logger.warning("Failed to collect metrics")
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.reporting_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Metrics collection took {elapsed:.2f}s, "
                        f"longer than interval {self.reporting_interval}s"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error in metrics reporting loop: {e}", exc_info=True)
                time.sleep(self.reporting_interval)
        
        self.logger.info("Metrics reporting loop stopped")
                
    def _collect_node_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect current node metrics"""
        try:
            system_metrics = self.metrics_collector.get_detailed_metrics()
            if not system_metrics:
                return None
                
            # Get container information
            containers = self.container_manager.list_containers()
            running_containers = len([c for c in containers if c.state == ContainerState.RUNNING])
            
            # Count warm containers and mark expired ones as dead
            warm_containers = 0
            current_time = time.time()
            for container in containers:
                if container.state == ContainerState.WARM:
                    if container.started_at and (current_time - container.started_at) > Config.DEFAULT_MAX_WARM_TIME:
                        container.state = ContainerState.DEAD
                    else:
                        warm_containers += 1

            # Get request tracking
            request_tracking = self.controller.get_request_tracking()
            active_requests = request_tracking["active_requests"]
            total_requests = request_tracking["total_requests"]
            response_times = request_tracking["response_times"]
            
            # Calculate average response time
            avg_response_time = 0.0
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                # Keep only recent response times (last 100)
                if len(response_times) > 100:
                    request_tracking["response_times"] = response_times[-100:]

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
            self.logger.error(f"Failed to collect node metrics: {e}", exc_info=True)
            return None
            
    def _send_metrics_to_central(self, metrics: Dict[str, Any]):
        """Send collected metrics to central node"""
        try:
            response = requests.post(
                f"{self.central_node_url}/api/v1/central/nodes/{self.node_id}/metrics",
                json=metrics,
                timeout=5
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to send metrics: {response.status_code}")
            else:
                self.logger.debug("Metrics sent successfully")
                
        except requests.Timeout:
            self.logger.warning("Timeout sending metrics to central node")
        except Exception as e:
            self.logger.error(f"Failed to send metrics to central node: {e}")
            
    def _cleanup_warm_containers(self, max_warm_time: int = Config.DEFAULT_MAX_WARM_TIME) -> None:
        """Clean up expired warm containers"""
        try:
            current_time = time.time()
            dead_containers = self.container_manager.list_containers(ContainerState.DEAD)

            cleaned_count = 0
            for container in dead_containers:
                if container.started_at and (current_time - container.started_at) > max_warm_time:
                    try:
                        self.container_manager.remove_container(container.container_id)
                        self.logger.info(f"Cleaned up dead container: {container.container_id[:12]}")
                        cleaned_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to remove container {container.container_id[:12]}: {e}")
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} dead containers")
                
        except Exception as e:
            self.logger.error(f"Error in cleanup_warm_containers: {e}", exc_info=True)
   
    def cleanup_warm_containers_loop(self):
        """Main cleanup loop"""
        self.logger.info("Cleanup warm containers loop started")
        
        while self.is_cleaning:
            try:
                loop_start = time.time()
                self._cleanup_warm_containers()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.cleanup_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Cleanup took {elapsed:.2f}s, "
                        f"longer than interval {self.cleanup_interval}s"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                time.sleep(self.cleanup_interval)
        
        self.logger.info("Cleanup warm containers loop stopped")

    def start_cleanup_containers(self):
        """Start cleanup thread"""
        if self.is_cleaning:
            self.logger.warning("Cleanup is already running")
            return
            
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(
            target=self.cleanup_warm_containers_loop,
            name=f"EdgeAgent-Cleanup-{self.node_id}"
        )
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup thread started")
        
    def stop_cleanup_containers(self):
        """Stop cleanup thread"""
        self.logger.info("Stopping cleanup thread...")
        self.is_cleaning = False
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
            
        self.logger.info("Cleanup thread stopped")

    def start_all_tasks(self):
        """Start all background tasks"""
        self.start_metrics_reporting()
        self.start_cleanup_containers()

    def stop_all_tasks(self):
        """Stop all background tasks"""
        self.stop_metrics_reporting()
        self.stop_cleanup_containers()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.stop_all_tasks()
        except:
            pass