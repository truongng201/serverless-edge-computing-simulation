import logging
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import psutil
import platform

@dataclass
class SystemMetrics:
    timestamp: float
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_available: int
    cpu_energy_kwh: float
    load_average: tuple
    uptime: float

class SystemMetricsCollector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._container_cpu_limit = self._get_container_cpu_limit()
        self._container_memory_limit = self._get_container_memory_limit()
        self._is_containerized = self._detect_container()
        self._cgroup_version = self._detect_cgroup_version()
        
        if self._is_containerized:
            self.logger.info(f"Running in container (cgroup v{self._cgroup_version}) - CPU limit: {self._container_cpu_limit} cores, Memory limit: {self._container_memory_limit / (1024**3):.2f} GB")
        else:
            self.logger.info("Running on host machine")
    
    def _detect_container(self) -> bool:
        """Detect if running inside a Docker container"""
        try:
            # Check for .dockerenv file
            if os.path.exists('/.dockerenv'):
                return True
            
            # Check cgroup
            if os.path.exists('/proc/1/cgroup'):
                with open('/proc/1/cgroup', 'rt') as f:
                    return 'docker' in f.read()
            
            return False
        except:
            return False
    
    def _detect_cgroup_version(self) -> int:
        """Detect cgroup version (v1 or v2)"""
        try:
            # Check if cgroup v2 is being used
            if os.path.exists('/sys/fs/cgroup/cgroup.controllers'):
                return 2
            elif os.path.exists('/sys/fs/cgroup/cpu'):
                return 1
            return 1  # Default to v1
        except:
            return 1
    
    def _get_container_cpu_limit(self) -> Optional[float]:
        """Get CPU limit from Docker container cgroup"""
        try:
            # Try cgroup v2 first
            cpu_max_path = '/sys/fs/cgroup/cpu.max'
            if os.path.exists(cpu_max_path):
                with open(cpu_max_path, 'r') as f:
                    content = f.read().strip().split()
                    if len(content) == 2 and content[0] != 'max':
                        quota = int(content[0])
                        period = int(content[1])
                        return quota / period
            
            # Try cgroup v1
            quota_path = '/sys/fs/cgroup/cpu/cpu.cfs_quota_us'
            period_path = '/sys/fs/cgroup/cpu/cpu.cfs_period_us'
            
            if os.path.exists(quota_path) and os.path.exists(period_path):
                with open(quota_path, 'r') as f:
                    quota = int(f.read().strip())
                with open(period_path, 'r') as f:
                    period = int(f.read().strip())
                
                if quota > 0 and period > 0:
                    return quota / period
            
            return None
        except Exception as e:
            self.logger.debug(f"Could not read container CPU limit: {e}")
            return None
    
    def _get_container_memory_limit(self) -> Optional[int]:
        """Get memory limit from Docker container cgroup"""
        try:
            # Try cgroup v2 first
            mem_max_path = '/sys/fs/cgroup/memory.max'
            if os.path.exists(mem_max_path):
                with open(mem_max_path, 'r') as f:
                    content = f.read().strip()
                    if content != 'max':
                        return int(content)
            
            # Try cgroup v1
            limit_path = '/sys/fs/cgroup/memory/memory.limit_in_bytes'
            if os.path.exists(limit_path):
                with open(limit_path, 'r') as f:
                    limit = int(f.read().strip())
                    # Check if it's a real limit (not the default huge value)
                    if limit < (1 << 62):  # Reasonable memory limit
                        return limit
            
            return None
        except Exception as e:
            self.logger.debug(f"Could not read container memory limit: {e}")
            return None
    
    def _get_container_memory_usage(self) -> Optional[int]:
        """Get current memory usage from Docker container cgroup"""
        try:
            # Try cgroup v2 first
            mem_current_path = '/sys/fs/cgroup/memory.current'
            if os.path.exists(mem_current_path):
                with open(mem_current_path, 'r') as f:
                    return int(f.read().strip())
            
            # Try cgroup v1
            usage_path = '/sys/fs/cgroup/memory/memory.usage_in_bytes'
            if os.path.exists(usage_path):
                with open(usage_path, 'r') as f:
                    return int(f.read().strip())
            
            return None
        except Exception as e:
            self.logger.debug(f"Could not read container memory usage: {e}")
            return None

    def _get_uptime(self) -> float:
        try:
            boot_time = psutil.boot_time()
            return time.time() - boot_time
        except Exception as e:
            self.logger.error(f"Failed to get uptime: {e}")
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get CPU usage considering container limits"""
        try:
            # Get raw CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # If running in container with CPU limit, scale the usage
            if self._container_cpu_limit is not None:
                total_cores = psutil.cpu_count()
                # Scale usage based on the limited cores
                cpu_usage = (cpu_usage / total_cores) * self._container_cpu_limit
            
            return cpu_usage
        except Exception as e:
            self.logger.error(f"Failed to read CPU usage: {e}")
            return 0.0
        
    def _get_load_average(self) -> tuple:
        try:
            if platform.system() == "Windows" or not hasattr(os, "getloadavg"):
                try:
                    cpu_percent = psutil.cpu_percent(interval=0)
                    cpu_cores = self._container_cpu_limit if self._container_cpu_limit else max(1, psutil.cpu_count() or 1)
                    approx_load = round((cpu_percent / 100.0) * cpu_cores, 2)
                    return (approx_load, approx_load, approx_load)
                except Exception:
                    return (0.0, 0.0, 0.0)
            return os.getloadavg()
        except Exception:
            return (0.0, 0.0, 0.0)
        
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory info considering container limits"""
        try:
            # If running in container with memory limit, use container stats
            if self._container_memory_limit is not None:
                total = self._container_memory_limit
                used = self._get_container_memory_usage()
                
                if used is not None:
                    available = total - used
                    usage_percentage = (used / total) * 100.0
                    
                    return {
                        'total': total,
                        'available': available,
                        'used': used,
                        'usage_percentage': usage_percentage
                    }
            
            # Fallback to psutil for host or if container stats unavailable
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'usage_percentage': mem.percent
            }
        except Exception as e:
            self.logger.error(f"Failed to read memory info: {e}")
            # Final fallback
            try:
                mem = psutil.virtual_memory()
                return {
                    'total': mem.total,
                    'available': mem.available,
                    'used': mem.used,
                    'usage_percentage': mem.percent
                }
            except:
                return {
                    'total': 0,
                    'available': 0,
                    'used': 0,
                    'usage_percentage': 0.0
                }
        
    def _collect_metrics(self) -> Optional[SystemMetrics]:
        try:
            timestamp = time.time()
            cpu_usage = self._get_cpu_usage()
            memory_info = self._get_memory_info()
            energy = self._calculate_cpu_energy(cpu_usage)
            load_avg = self._get_load_average()
            uptime = self._get_uptime()
            
            return SystemMetrics(
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory_info['usage_percentage'],
                memory_total=memory_info['total'],
                memory_available=memory_info['available'],
                cpu_energy_kwh=energy,
                load_average=load_avg,
                uptime=uptime
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return None
    
    def _calculate_cpu_energy(self, cpu_usage_percent: float) -> float:
        try:
            # Adjust base power for container CPU limits
            if self._container_cpu_limit is not None:
                base_power_watts = 50 * (self._container_cpu_limit / psutil.cpu_count())
                max_additional_watts = 100 * (self._container_cpu_limit / psutil.cpu_count())
            else:
                base_power_watts = 50
                max_additional_watts = 100
            
            current_power_watts = base_power_watts + (max_additional_watts * cpu_usage_percent / 100.0)
            measurement_interval_hours = 1.0 / 3600.0
            energy_kwh = (current_power_watts / 1000.0) * measurement_interval_hours
            return energy_kwh
        except Exception as e:
            self.logger.error(f"Failed to calculate CPU energy: {e}")
            return 0.0
    
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        base_metrics = self._collect_metrics()
        if not base_metrics:
            return {}
        
        return {
            'timestamp': base_metrics.timestamp,
            'cpu_usage': base_metrics.cpu_usage,
            'memory_usage': base_metrics.memory_usage,
            'memory_total': base_metrics.memory_total,
            'memory_available': base_metrics.memory_available,
            'cpu_energy_kwh': base_metrics.cpu_energy_kwh,
            'load_average': base_metrics.load_average,
            'uptime': base_metrics.uptime,
            'is_containerized': self._is_containerized,
            'container_cpu_limit': self._container_cpu_limit,
            'container_memory_limit': self._container_memory_limit,
            'cgroup_version': self._cgroup_version,
        }
        
    def get_system_info(self) -> Dict[str, Any]:
        try:
            # Use container limits if available
            cpu_cores = self._container_cpu_limit if self._container_cpu_limit else psutil.cpu_count(logical=True)
            memory_total = self._container_memory_limit if self._container_memory_limit else psutil.virtual_memory().total
            
            system_info = {
                "platform": platform.system(),
                "node_name": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_cores_physical": cpu_cores if isinstance(cpu_cores, int) else round(cpu_cores, 2),
                "memory_total": round(memory_total / (1024**3), 2),
                "disk_size_total": 0,
                "is_containerized": self._is_containerized,
            }

            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    system_info["disk_size_total"] += round(usage.total / (1024**3), 2)
                except:
                    continue
            return system_info
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}