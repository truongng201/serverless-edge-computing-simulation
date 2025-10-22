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
        
    def _get_uptime(self) -> float:
        try:
            boot_time = psutil.boot_time()
            return time.time() - boot_time
        except Exception as e:
            self.logger.error(f"Failed to get uptime: {e}")
            return 0.0

    def _get_cpu_usage(self) -> float:
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            self.logger.error(f"Failed to read CPU usage: {e}")
            return 0.0
        
    def _get_load_average(self) -> tuple:
        try:
            if platform.system() == "Windows" or not hasattr(os, "getloadavg"):
                try:
                    cpu_percent = psutil.cpu_percent(interval=0)
                    cpu_cores = max(1, psutil.cpu_count() or 1)
                    approx_load = round((cpu_percent / 100.0) * cpu_cores, 2)
                    return (approx_load, approx_load, approx_load)
                except Exception:
                    return (0.0, 0.0, 0.0)
            return os.getloadavg()
        except Exception:
            return (0.0, 0.0, 0.0)
        
    def _get_memory_info(self) -> Dict[str, Any]:
        try:
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'usage_percentage': mem.percent
            }
        except Exception as e:
            self.logger.error(f"Failed to read memory info: {e}")
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
        }
        
    def get_system_info(self) -> Dict[str, Any]:
        try:
            system_info = {
                "platform": platform.system(),
                "node_name": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_cores_physical": psutil.cpu_count(logical=True),
                "memory_total": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_size_total": 0,
            }

            for part in psutil.disk_partitions():
                usage = psutil.disk_usage(part.mountpoint)
                system_info["disk_size_total"] += round(usage.total / (1024**3), 2)
            return system_info
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}