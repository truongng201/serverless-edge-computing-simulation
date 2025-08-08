"""
Edge Node API Layer
Handles container execution requests and reports metrics to central node
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify, Blueprint
import requests

from shared.docker_manager import DockerManager, ContainerState
from shared.system_metrics import SystemMetricsCollector
from config import Config

# Create blueprint for edge node API
edge_api = Blueprint('edge_api', __name__, url_prefix=Config.EDGE_API_PREFIX)

class EdgeNodeAPI:
    def __init__(self, node_id: str, central_node_url: str):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.central_node_url = central_node_url
        
        # Initialize managers
        self.docker_manager = DockerManager()
        self.metrics_collector = SystemMetricsCollector()
        
        # Metrics reporting
        self.metrics_thread = None
        self.is_reporting = False
        self.reporting_interval = Config.METRICS_COLLECTION_INTERVAL
        
        # Request tracking
        self.active_requests = 0
        self.total_requests = 0
        self.response_times = []
        
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
        docker_info = self.docker_manager.get_docker_info()
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
            containers = self.docker_manager.list_containers()
            running_containers = len([c for c in containers if c.state == ContainerState.RUNNING])
            
            # Calculate average response time
            avg_response_time = 0.0
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                # Keep only recent response times (last 100)
                self.response_times = self.response_times[-100:]
                
            return {
                "cpu_usage": system_metrics["cpu_usage"] / 100.0,  # Convert to 0-1 range
                "memory_usage": system_metrics["memory_usage"] / 100.0,  # Convert to 0-1 range
                "network_io": system_metrics["network_io"],
                "disk_io": system_metrics["disk_io"],
                "container_count": running_containers,
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
            function_id = function_data.get("function_id")
            image = function_data.get("image", Config.DEFAULT_CONTAINER_IMAGE)
            environment = function_data.get("environment", {})
            
            # Check if we need to create a new container or reuse existing
            container_id = self._get_or_create_container(function_id, image, environment)
            
            if not container_id:
                return {
                    "success": False,
                    "error": "Failed to create container",
                    "execution_time": time.time() - start_time
                }
                
            # Execute the function
            result = self._execute_in_container(container_id, function_data)
            
            execution_time = time.time() - start_time
            self.response_times.append(execution_time)
            
            return {
                "success": True,
                "result": result,
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
            
    def _get_or_create_container(self, function_id: str, image: str, environment: Dict[str, str]) -> Optional[str]:
        """Get existing container or create new one"""
        # Check for existing idle container for this function
        containers = self.docker_manager.list_containers(ContainerState.IDLE)
        for container in containers:
            if container.name == f"function_{function_id}":
                # Reuse existing container (warm start)
                if self.docker_manager.start_container(container.container_id):
                    self.logger.info(f"Warm start for function {function_id}")
                    return container.container_id
                    
        # Create new container (cold start)
        container_id = self.docker_manager.create_container(
            name=f"function_{function_id}_{int(time.time())}",
            image=image,
            environment=environment
        )
        
        if container_id and self.docker_manager.start_container(container_id):
            self.logger.info(f"Cold start for function {function_id}")
            return container_id
            
        return None
        
    def _execute_in_container(self, container_id: str, function_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function logic in container"""
        # This is a simplified execution - in practice, you would
        # send the actual function code/data to the container
        # and execute it, then return the results
        
        # For simulation, we'll just return some dummy results
        execution_result = {
            "function_id": function_data.get("function_id"),
            "executed_at": time.time(),
            "status": "completed",
            "output": f"Function {function_data.get('function_id')} executed successfully"
        }
        
        # Simulate some execution time
        time.sleep(0.1)  # 100ms execution time
        
        return execution_result
        
    def cleanup_idle_containers(self, max_idle_time: int = 300):
        """Clean up containers that have been idle too long"""
        current_time = time.time()
        idle_containers = self.docker_manager.list_containers(ContainerState.IDLE)
        
        for container in idle_containers:
            if container.stopped_at and (current_time - container.stopped_at) > max_idle_time:
                self.docker_manager.remove_container(container.container_id)
                self.logger.info(f"Cleaned up idle container: {container.container_id[:12]}")
                
    def get_node_status(self) -> Dict[str, Any]:
        """Get current node status"""
        system_metrics = self.metrics_collector.collect_metrics()
        containers = self.docker_manager.list_containers()
        
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

# Global instance (will be initialized by the edge node app)
edge_node_api: Optional[EdgeNodeAPI] = None

def initialize_edge_api(node_id: str, central_node_url: str):
    """Initialize the edge node API"""
    global edge_node_api
    edge_node_api = EdgeNodeAPI(node_id, central_node_url)
    return edge_node_api

# API Routes
@edge_api.route('/execute', methods=['POST'])
def execute_function():
    """Execute a serverless function"""
    if not edge_node_api:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No function data provided"}), 400
        
    result = edge_node_api.execute_function(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@edge_api.route('/status', methods=['GET'])
def get_status():
    """Get edge node status"""
    if not edge_node_api:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    status = edge_node_api.get_node_status()
    return jsonify(status)

@edge_api.route('/containers', methods=['GET'])
def list_containers():
    """List containers on this edge node"""
    if not edge_node_api:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    containers = edge_node_api.docker_manager.list_containers()
    container_list = [
        {
            "container_id": c.container_id,
            "name": c.name,
            "state": c.state.value,
            "created_at": c.created_at,
            "image": c.image
        }
        for c in containers
    ]
    
    return jsonify({"containers": container_list})

@edge_api.route('/containers/<container_id>/stats', methods=['GET'])
def get_container_stats(container_id):
    """Get container statistics"""
    if not edge_node_api:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    stats = edge_node_api.docker_manager.get_container_stats(container_id)
    if stats:
        return jsonify(stats)
    else:
        return jsonify({"success": False, "error": "Container not found or stats unavailable"}), 404

@edge_api.route('/cleanup', methods=['POST'])
def cleanup_containers():
    """Clean up idle containers"""
    if not edge_node_api:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    max_idle_time = request.json.get('max_idle_time', 300) if request.json else 300
    edge_node_api.cleanup_idle_containers(max_idle_time)
    
    return jsonify({"success": True, "message": "Cleanup completed"})

@edge_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "node_id": edge_node_api.node_id if edge_node_api else "unknown"
    })

def register_edge_api(app: Flask):
    """Register edge node API with Flask app"""
    app.register_blueprint(edge_api)
    logging.getLogger(__name__).info("Edge Node API registered")
