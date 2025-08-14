"""
Resource Layer - System Metrics Collection
Collects real-time system metrics from /proc files
"""

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
        self.last_cpu_times = None
        self.last_cpu_measurement_time = None
        
    def collect_metrics(self) -> Optional[SystemMetrics]:
        """Collect all system metrics"""
        try:
            timestamp = time.time()
            cpu_usage = self.get_cpu_usage()
            memory_info = self.get_memory_info()
            energy = self.calculate_cpu_energy(cpu_usage)
            load_avg = self.get_load_average()
            uptime = self.get_uptime()
            
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
            
    def get_cpu_usage(self) -> float:
        """Get CPU usage percentage using psutil"""
        try:
            # psutil.cpu_percent() returns the CPU utilization as a percentage
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            self.logger.error(f"Failed to read CPU usage: {e}")
            return 0.0
            
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information using psutil"""
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
            
    def calculate_cpu_energy(self, cpu_usage_percent: float) -> float:
        """Calculate CPU energy consumption in kWh"""
        try:
            # Simple energy calculation based on CPU usage
            # Base power consumption + variable power based on usage
            base_power_watts = 50  # Base power consumption
            max_additional_watts = 100  # Additional power at 100% CPU
            
            # Current power consumption
            current_power_watts = base_power_watts + (max_additional_watts * cpu_usage_percent / 100.0)
            
            # Calculate energy for the measurement interval (assume 1 second)
            measurement_interval_hours = 1.0 / 3600.0  # 1 second in hours
            energy_kwh = (current_power_watts / 1000.0) * measurement_interval_hours
            
            return energy_kwh
            
        except Exception as e:
            self.logger.error(f"Failed to calculate CPU energy: {e}")
            return 0.0
            
    def get_load_average(self) -> tuple:
        """Get system load average using os.getloadavg()"""
        try:
            return os.getloadavg()
        except Exception as e:
            self.logger.error(f"Failed to get load average: {e}")
            return (0.0, 0.0, 0.0)
            
    def get_uptime(self) -> float:
        """Get system uptime in seconds using psutil"""
        try:
            boot_time = psutil.boot_time()
            return time.time() - boot_time
        except Exception as e:
            self.logger.error(f"Failed to get uptime: {e}")
            return 0.0
            
    def get_network_io(self) -> Dict[str, Any]:
        """Get network I/O statistics using psutil"""
        try:
            net_io = psutil.net_io_counters(pernic=True)
            network_stats = {}
            total_rx = 0
            total_tx = 0
            for interface, stats in net_io.items():
                if interface != 'lo':  # Skip loopback interface
                    network_stats[interface] = {
                        'rx_bytes': stats.bytes_recv,
                        'rx_packets': stats.packets_recv,
                        'tx_bytes': stats.bytes_sent,
                        'tx_packets': stats.packets_sent
                    }
                    total_rx += stats.bytes_recv
                    total_tx += stats.bytes_sent
            return {
                'interfaces': network_stats,
                'total_rx_bytes': total_rx,
                'total_tx_bytes': total_tx
            }
        except Exception as e:
            self.logger.error(f"Failed to get network stats: {e}")
            return {'interfaces': {}, 'total_rx_bytes': 0, 'total_tx_bytes': 0}
            
    def get_disk_io(self) -> Dict[str, Any]:
        """Get disk I/O statistics using psutil"""
        try:
            disk_io = psutil.disk_io_counters(perdisk=True)
            disk_stats = {}
            for device, stats in disk_io.items():
                disk_stats[device] = {
                    'read_count': stats.read_count,
                    'write_count': stats.write_count,
                    'read_bytes': stats.read_bytes,
                    'write_bytes': stats.write_bytes,
                    'read_time': stats.read_time,
                    'write_time': stats.write_time
                }
            return disk_stats
        except Exception as e:
            self.logger.error(f"Failed to get disk stats: {e}")
            return {}
            
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics including network and disk I/O"""
        base_metrics = self.collect_metrics()
        if not base_metrics:
            return {}
            
        # network_io = self.get_network_io()
        # disk_io = self.get_disk_io()
        
        return {
            'timestamp': base_metrics.timestamp,
            'cpu_usage': base_metrics.cpu_usage,
            'memory_usage': base_metrics.memory_usage,
            'memory_total': base_metrics.memory_total,
            'memory_available': base_metrics.memory_available,
            'cpu_energy_kwh': base_metrics.cpu_energy_kwh,
            'load_average': base_metrics.load_average,
            'uptime': base_metrics.uptime,
            # 'network_io': network_io,
            # 'disk_io': disk_io
        }

    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            system_info = {
                "platform": platform.system(),
                "node_name": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_cores_logical": psutil.cpu_count(logical=True),
                "cpu_cores_physical": psutil.cpu_count(logical=False),
                "memory_total": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_size_total": 0,
            }

            # Get disk information
            for part in psutil.disk_partitions():
                usage = psutil.disk_usage(part.mountpoint)
                system_info["disk_size_total"] += round(usage.total / (1024**3), 2)

            return system_info

        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}