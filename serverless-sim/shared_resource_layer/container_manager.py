"""
Resource Layer - Docker Container Management
Handles Docker container lifecycle and state management
"""

import docker
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from config import ContainerState, Config

@dataclass
class ContainerInfo:
    container_id: str
    name: str
    image: str
    state: ContainerState
    created_at: float
    started_at: Optional[float]
    stopped_at: Optional[float]
    ports: Dict[str, int]
    resource_limits: Dict[str, str]

class ContainerManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.client = docker.DockerClient(base_url=Config.DOCKER_SOCKET)
            # Test connection
            self.client.ping()
            self._create_network()
            self.logger.info("Docker client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
            
        self.containers: Dict[str, ContainerInfo] = {}
        
    def _create_network(self):
        """Create a new Docker network"""
        if not self.client:
            self.logger.error("Docker client not available")
            return
        
        try:
            # Check if current network exist
            self.client.networks.get(Config.CONTAINER_NETWORK)
            self.logger.info(f"Docker network {Config.CONTAINER_NETWORK} already exists")
        except docker.errors.NotFound:
            self.client.networks.create(Config.CONTAINER_NETWORK)
            self.logger.info(f"Docker network {Config.CONTAINER_NETWORK} created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create Docker network {Config.CONTAINER_NETWORK}: {e}")
            
    def create_container(self, name: str, image: str = None,
                        ports: Dict[str, int] = None,
                        resource_limits: Dict[str, str] = None) -> Optional[str]:
        """Create a new container (COLD_START state)"""
        if not self.client:
            self.logger.error("Docker client not available")
            return None
            
        try:
            image = image or Config.DEFAULT_CONTAINER_IMAGE
            ports = ports or {}
            resource_limits = resource_limits or {"memory": Config.DEFAULT_CONTAINER_MEMORY_LIMIT}
            
            # Create container
            container = self.client.containers.create(
                image=image,
                name=name,
                detach=Config.DEFAULT_CONTAINER_DETACH_MODE,
                ports=ports,
                mem_limit=resource_limits.get("memory", Config.DEFAULT_CONTAINER_MEMORY_LIMIT),
                network=Config.CONTAINER_NETWORK if hasattr(Config, 'CONTAINER_NETWORK') else None
            )
            container_id = container.id[:12]  # Shorten ID for display
            
            container_info = ContainerInfo(
                container_id=container_id,
                name=name,
                image=image,
                state=ContainerState.INIT,
                created_at=time.time(),
                started_at=None,
                stopped_at=None,
                ports=ports,
                resource_limits=resource_limits
            )
            
            self.containers[container_id] = container_info

            self.logger.info(f"Container created: {name} ({container_id})")
            return container_id

        except Exception as e:
            self.logger.error(f"Failed to create container {name}: {e}")
            return None
            
    def run_container(self, container_id: str) -> str:
        """Start a container (COLD_START -> RUNNING -> IDLE)"""
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_id)
            container.start()

            if container_id in self.containers:
                self.containers[container_id].state = ContainerState.RUNNING
                self.containers[container_id].started_at = time.time()

            self.logger.info(f"Container started: {container_id[:12]}")

            container.wait()

            # Get logs from container
            output_logs = container.logs().decode("utf-8").strip()

            # Mark as IDLE after completion
            if container_id in self.containers:
                self.containers[container_id].state = ContainerState.IDLE
                self.containers[container_id].stopped_at = time.time()

            marker = "Result of function"
            if marker in output_logs:
                final_result = output_logs.split(marker)[-1].strip()
            else:
                final_result = output_logs.strip()

            return final_result
        except docker.errors.NotFound:
            self.logger.error(f"Container {container_id} not found")
            return None
        except Exception as e:
            self.logger.error(f"Failed to start container {container_id}: {e}")
            return None

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container (IDLE -> DEAD)"""
        if not self.client:
            return False
            
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            
            if container_id in self.containers:
                del self.containers[container_id]
                
            self.logger.info(f"Container removed: {container_id[:12]}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove container {container_id}: {e}")
            return False
            
    def get_container_info(self, container_id: str) -> Optional[ContainerInfo]:
        """Get container information"""
        return self.containers.get(container_id)
        
    def list_containers(self, state: Optional[ContainerState] = None) -> List[ContainerInfo]:
        """List containers, optionally filtered by state"""
        if state:
            return [info for info in self.containers.values() if info.state == state]
        return list(self.containers.values())
        
    def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time container statistics"""
        if not self.client:
            return None
            
        try:
            container = self.client.containers.get(container_id)
            
            # Get container stats (non-streaming)
            stats = container.stats(stream=False)
            
            # Parse CPU usage
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})
            
            cpu_usage = self._calculate_cpu_usage(cpu_stats, precpu_stats)
            
            # Parse memory usage
            memory_stats = stats.get('memory_stats', {})
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 1)
            memory_percentage = (memory_usage / memory_limit) if memory_limit > 0 else 0
            
            return {
                'container_id': container_id,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'memory_percentage': memory_percentage,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats for container {container_id}: {e}")
            return None
            
    def _calculate_cpu_usage(self, cpu_stats: Dict, precpu_stats: Dict) -> float:
        """Calculate CPU usage percentage"""
        try:
            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                       precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                          precpu_stats.get('system_cpu_usage', 0)
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_count = cpu_stats.get('online_cpus', 1)
                return (cpu_delta / system_delta) * cpu_count * 100.0
            return 0.0
            
        except Exception:
            return 0.0
            
    def cleanup_dead_containers(self):
        """Clean up containers marked as DEAD"""
        dead_containers = [
            container_id for container_id, info in self.containers.items()
            if info.state == ContainerState.DEAD
        ]
        
        for container_id in dead_containers:
            del self.containers[container_id]
            
        self.logger.info(f"Cleaned up {len(dead_containers)} dead containers")
        
    def get_docker_info(self) -> Optional[Dict[str, Any]]:
        """Get Docker daemon information"""
        if not self.client:
            return None
            
        try:
            info = self.client.info()
            return {
                'containers': info.get('Containers', 0),
                'images': info.get('Images', 0),
                'server_version': info.get('ServerVersion', 'unknown'),
                'memory_total': info.get('MemTotal', 0),
                'cpus': info.get('NCPU', 0)
            }
        except Exception as e:
            self.logger.error(f"Failed to get Docker info: {e}")
            return None
