"""
Resource Layer - System Metrics Collection
Collects real-time system metrics from /proc files
"""

import logging
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

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
        """Get CPU usage percentage from /proc/stat"""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                
            # Parse CPU times
            times = [int(x) for x in line.split()[1:]]
            
            # Calculate total and idle time
            total_time = sum(times)
            idle_time = times[3]  # idle time is the 4th value
            
            current_time = time.time()
            
            if self.last_cpu_times is not None and self.last_cpu_measurement_time is not None:
                # Calculate differences
                total_diff = total_time - self.last_cpu_times[0]
                idle_diff = idle_time - self.last_cpu_times[1]
                
                if total_diff > 0:
                    cpu_usage = ((total_diff - idle_diff) / total_diff) * 100.0
                else:
                    cpu_usage = 0.0
            else:
                cpu_usage = 0.0
                
            # Store current values for next calculation
            self.last_cpu_times = (total_time, idle_time)
            self.last_cpu_measurement_time = current_time
            
            return max(0.0, min(100.0, cpu_usage))
            
        except Exception as e:
            self.logger.error(f"Failed to read CPU usage: {e}")
            return 0.0
            
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information from /proc/meminfo"""
        try:
            memory_info = {}
            
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith(('MemTotal:', 'MemFree:', 'MemAvailable:', 'Buffers:', 'Cached:')):
                        key, value = line.split(':')
                        # Convert kB to bytes
                        memory_info[key] = int(value.split()[0]) * 1024
                        
            total = memory_info.get('MemTotal', 0)
            available = memory_info.get('MemAvailable', memory_info.get('MemFree', 0))
            
            # Add buffers and cached to available if MemAvailable is not present
            if 'MemAvailable' not in memory_info:
                available += memory_info.get('Buffers', 0) + memory_info.get('Cached', 0)
                
            used = total - available
            usage_percentage = (used / total * 100.0) if total > 0 else 0.0
            
            return {
                'total': total,
                'available': available,
                'used': used,
                'usage_percentage': usage_percentage
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
        """Get system load average"""
        try:
            with open('/proc/loadavg', 'r') as f:
                load_data = f.read().strip().split()
                
            return (
                float(load_data[0]),  # 1 minute
                float(load_data[1]),  # 5 minutes
                float(load_data[2])   # 15 minutes
            )
            
        except Exception as e:
            self.logger.error(f"Failed to read load average: {e}")
            return (0.0, 0.0, 0.0)
            
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
            return uptime_seconds
            
        except Exception as e:
            self.logger.error(f"Failed to read uptime: {e}")
            return 0.0
            
    def get_network_io(self) -> Dict[str, Any]:
        """Get network I/O statistics"""
        try:
            network_stats = {}
            
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
                
            for line in lines[2:]:  # Skip header lines
                parts = line.split(':')
                if len(parts) != 2:
                    continue
                    
                interface = parts[0].strip()
                stats = parts[1].split()
                
                if interface != 'lo':  # Skip loopback interface
                    network_stats[interface] = {
                        'rx_bytes': int(stats[0]),
                        'rx_packets': int(stats[1]),
                        'tx_bytes': int(stats[8]),
                        'tx_packets': int(stats[9])
                    }
                    
            # Calculate totals
            total_rx = sum(stats['rx_bytes'] for stats in network_stats.values())
            total_tx = sum(stats['tx_bytes'] for stats in network_stats.values())
            
            return {
                'interfaces': network_stats,
                'total_rx_bytes': total_rx,
                'total_tx_bytes': total_tx
            }
            
        except Exception as e:
            self.logger.error(f"Failed to read network stats: {e}")
            return {'interfaces': {}, 'total_rx_bytes': 0, 'total_tx_bytes': 0}
            
    def get_disk_io(self) -> Dict[str, Any]:
        """Get disk I/O statistics"""
        try:
            disk_stats = {}
            
            with open('/proc/diskstats', 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                parts = line.split()
                if len(parts) >= 14:
                    device = parts[2]
                    
                    # Only include actual disk devices (not partitions)
                    if device.startswith(('sd', 'hd', 'vd', 'nvme')):
                        disk_stats[device] = {
                            'read_ios': int(parts[3]),
                            'read_sectors': int(parts[5]),
                            'write_ios': int(parts[7]),
                            'write_sectors': int(parts[9]),
                            'io_time': int(parts[12])
                        }
                        
            return disk_stats
            
        except Exception as e:
            self.logger.error(f"Failed to read disk stats: {e}")
            return {}
            
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics including network and disk I/O"""
        base_metrics = self.collect_metrics()
        if not base_metrics:
            return {}
            
        network_io = self.get_network_io()
        disk_io = self.get_disk_io()
        
        return {
            'timestamp': base_metrics.timestamp,
            'cpu_usage': base_metrics.cpu_usage,
            'memory_usage': base_metrics.memory_usage,
            'memory_total': base_metrics.memory_total,
            'memory_available': base_metrics.memory_available,
            'cpu_energy_kwh': base_metrics.cpu_energy_kwh,
            'load_average': base_metrics.load_average,
            'uptime': base_metrics.uptime,
            'network_io': network_io,
            'disk_io': disk_io
        }
