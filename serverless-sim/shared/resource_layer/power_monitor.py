"""
Real-Time Power Monitoring using Intel RAPL (Running Average Power Limit)

This module reads actual power consumption from the server's hardware sensors
instead of using estimated values. RAPL provides CPU package and DRAM power
readings with ~1ms granularity.

Usage:
    monitor = RAPLPowerMonitor()
    
    # Get instantaneous power (samples over 100ms)
    power = monitor.get_current_power()
    print(f"Current power: {power:.2f} W")
    
    # Get energy over a period
    energy = monitor.measure_energy(duration_seconds=1.0)
    print(f"Energy consumed: {energy:.2f} J")

Requirements:
    - Intel CPU with RAPL support
    - Read access to /sys/class/powercap/intel-rapl:* 
    - May require: sudo chmod a+r /sys/class/powercap/intel-rapl:*/energy_uj

References:
    - Intel 64 and IA-32 Architectures SDM, Vol. 3B, Chapter 14.9
    - https://www.kernel.org/doc/html/latest/power/powercap/powercap.html
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class RAPLReading:
    """A single RAPL energy reading."""
    timestamp: float           # Time of reading (time.time())
    energy_uj: int             # Energy in microjoules
    domain: str                # RAPL domain name (package-0, core, dram, etc.)
    
    def energy_joules(self) -> float:
        """Convert to Joules."""
        return self.energy_uj / 1_000_000


@dataclass 
class PowerSample:
    """Power measurement between two RAPL readings."""
    timestamp: float           # Midpoint time
    power_watts: float         # Average power in Watts
    duration_s: float          # Sampling duration
    domain: str                # RAPL domain
    cpu_percent: float         # CPU utilization during sample


class RAPLPowerMonitor:
    """
    Real-time power monitor using Intel RAPL interface.
    
    RAPL (Running Average Power Limit) provides energy counters for:
    - package: Entire CPU socket (cores + uncore)
    - core: CPU cores only
    - uncore: GPU, memory controller, etc.
    - dram: DRAM power (if available)
    """
    
    POWERCAP_PATH = Path("/sys/class/powercap")
    
    def __init__(self):
        self.domains: Dict[str, Path] = {}
        self.max_energy: Dict[str, int] = {}
        self.available = False
        self._last_reading: Dict[str, RAPLReading] = {}
        
        self._discover_domains()
    
    def _discover_domains(self):
        """Find available RAPL domains."""
        if not self.POWERCAP_PATH.exists():
            logging.warning("powercap not available - RAPL not supported")
            return
        
        # Find all intel-rapl domains
        for item in self.POWERCAP_PATH.iterdir():
            if item.name.startswith("intel-rapl:"):
                energy_file = item / "energy_uj"
                name_file = item / "name"
                max_range_file = item / "max_energy_range_uj"
                
                if energy_file.exists() and name_file.exists():
                    try:
                        domain_name = name_file.read_text().strip()
                        self.domains[domain_name] = energy_file
                        
                        # Get max energy range for overflow detection
                        if max_range_file.exists():
                            self.max_energy[domain_name] = int(
                                max_range_file.read_text().strip()
                            )
                        
                        # Check for sub-domains (core, uncore, dram)
                        for subitem in item.iterdir():
                            if subitem.is_dir() and subitem.name.startswith("intel-rapl:"):
                                sub_energy = subitem / "energy_uj"
                                sub_name = subitem / "name"
                                sub_max = subitem / "max_energy_range_uj"
                                
                                if sub_energy.exists() and sub_name.exists():
                                    sub_domain = sub_name.read_text().strip()
                                    full_name = f"{domain_name}/{sub_domain}"
                                    self.domains[full_name] = sub_energy
                                    
                                    if sub_max.exists():
                                        self.max_energy[full_name] = int(
                                            sub_max.read_text().strip()
                                        )
                    except PermissionError:
                        logging.warning(
                            f"Permission denied reading {energy_file}. "
                            "Try: sudo chmod a+r /sys/class/powercap/intel-rapl:*/energy_uj"
                        )
                    except Exception as e:
                        logging.warning(f"Error reading RAPL domain: {e}")
        
        self.available = len(self.domains) > 0
        if self.available:
            logging.info(f"RAPL domains discovered: {list(self.domains.keys())}")
        else:
            logging.warning("No RAPL domains found - using estimation fallback")
    
    def read_energy(self, domain: str = "package-0") -> Optional[RAPLReading]:
        """
        Read current energy counter for a domain.
        
        Args:
            domain: RAPL domain name (package-0, package-0/core, package-0/dram)
            
        Returns:
            RAPLReading or None if not available
        """
        if domain not in self.domains:
            return None
        
        try:
            energy_uj = int(self.domains[domain].read_text().strip())
            return RAPLReading(
                timestamp=time.time(),
                energy_uj=energy_uj,
                domain=domain
            )
        except PermissionError:
            logging.error(f"Permission denied reading RAPL. Run: sudo chmod a+r {self.domains[domain]}")
            return None
        except Exception as e:
            logging.error(f"Error reading RAPL: {e}")
            return None
    
    def get_current_power(
        self, 
        domain: str = "package-0",
        sample_duration_s: float = 0.1
    ) -> Optional[PowerSample]:
        """
        Get current power consumption by sampling over a short period.
        
        Args:
            domain: RAPL domain to measure
            sample_duration_s: Sampling period (default 100ms)
            
        Returns:
            PowerSample with current power in Watts
        """
        # First reading
        start = self.read_energy(domain)
        if start is None:
            return None
        
        # Get CPU utilization during sample
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=sample_duration_s)
        else:
            time.sleep(sample_duration_s)
            cpu_percent = 0.0
        
        # Second reading
        end = self.read_energy(domain)
        if end is None:
            return None
        
        # Calculate power
        duration = end.timestamp - start.timestamp
        energy_diff = end.energy_uj - start.energy_uj
        
        # Handle counter overflow
        if energy_diff < 0 and domain in self.max_energy:
            energy_diff += self.max_energy[domain]
        
        power_watts = (energy_diff / 1_000_000) / duration if duration > 0 else 0.0
        
        return PowerSample(
            timestamp=(start.timestamp + end.timestamp) / 2,
            power_watts=power_watts,
            duration_s=duration,
            domain=domain,
            cpu_percent=cpu_percent
        )
    
    def measure_energy(
        self,
        duration_seconds: float,
        domain: str = "package-0",
        include_cpu_util: bool = True
    ) -> Tuple[float, float]:
        """
        Measure total energy consumption over a period.
        
        Args:
            duration_seconds: Measurement duration
            domain: RAPL domain
            include_cpu_util: Whether to track CPU utilization
            
        Returns:
            Tuple of (energy_joules, avg_cpu_percent)
        """
        start = self.read_energy(domain)
        if start is None:
            return 0.0, 0.0
        
        # Collect CPU samples
        cpu_samples = []
        sample_interval = min(0.5, duration_seconds / 10)
        elapsed = 0.0
        
        while elapsed < duration_seconds:
            if include_cpu_util and psutil:
                cpu_samples.append(psutil.cpu_percent(interval=sample_interval))
            else:
                time.sleep(sample_interval)
            elapsed += sample_interval
        
        end = self.read_energy(domain)
        if end is None:
            return 0.0, 0.0
        
        # Calculate energy
        energy_diff = end.energy_uj - start.energy_uj
        if energy_diff < 0 and domain in self.max_energy:
            energy_diff += self.max_energy[domain]
        
        energy_joules = energy_diff / 1_000_000
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        
        return energy_joules, avg_cpu
    
    def get_all_domains_power(
        self, 
        sample_duration_s: float = 0.1
    ) -> Dict[str, PowerSample]:
        """
        Get power consumption for all available RAPL domains.
        
        Returns:
            Dict mapping domain name to PowerSample
        """
        results = {}
        
        # Read all domains at once (start)
        start_readings = {
            domain: self.read_energy(domain) 
            for domain in self.domains
        }
        
        # Wait and get CPU utilization
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=sample_duration_s)
        else:
            time.sleep(sample_duration_s)
            cpu_percent = 0.0
        
        # Read all domains (end)
        end_readings = {
            domain: self.read_energy(domain) 
            for domain in self.domains
        }
        
        # Calculate power for each domain
        for domain in self.domains:
            start = start_readings.get(domain)
            end = end_readings.get(domain)
            
            if start and end:
                duration = end.timestamp - start.timestamp
                energy_diff = end.energy_uj - start.energy_uj
                
                if energy_diff < 0 and domain in self.max_energy:
                    energy_diff += self.max_energy[domain]
                
                power_watts = (energy_diff / 1_000_000) / duration if duration > 0 else 0.0
                
                results[domain] = PowerSample(
                    timestamp=(start.timestamp + end.timestamp) / 2,
                    power_watts=power_watts,
                    duration_s=duration,
                    domain=domain,
                    cpu_percent=cpu_percent
                )
        
        return results
    
    def is_available(self) -> bool:
        """Check if RAPL monitoring is available."""
        return self.available
    
    def get_available_domains(self) -> List[str]:
        """Get list of available RAPL domains."""
        return list(self.domains.keys())


class PowerMonitor:
    """
    Unified power monitor that uses RAPL if available, falls back to estimation.
    """
    
    def __init__(self):
        self.rapl = RAPLPowerMonitor()
        self.use_rapl = self.rapl.is_available()
        
        if self.use_rapl:
            logging.info("Using RAPL for real power measurements")
        else:
            logging.info("RAPL not available, using power estimation")
    
    def get_current_power(self, sample_duration_s: float = 0.1) -> Dict[str, float]:
        """
        Get current power consumption.
        
        Returns:
            Dict with 'power_watts', 'cpu_percent', 'source' ('rapl' or 'estimate')
        """
        if self.use_rapl:
            sample = self.rapl.get_current_power(sample_duration_s=sample_duration_s)
            if sample:
                return {
                    'power_watts': sample.power_watts,
                    'cpu_percent': sample.cpu_percent,
                    'source': 'rapl',
                    'domain': sample.domain
                }
        
        # Fallback to estimation
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=sample_duration_s)
            # Simple estimation: assume 15W TDP, idle at 35%
            estimated_power = 5.25 + (15.0 - 5.25) * (cpu_percent / 100) ** 1.2
            return {
                'power_watts': estimated_power,
                'cpu_percent': cpu_percent,
                'source': 'estimate'
            }
        
        return {'power_watts': 0.0, 'cpu_percent': 0.0, 'source': 'unavailable'}
    
    def measure_energy(self, duration_seconds: float) -> Dict[str, float]:
        """
        Measure energy consumption over a period.
        
        Returns:
            Dict with 'energy_joules', 'avg_power_watts', 'avg_cpu_percent', 'source'
        """
        if self.use_rapl:
            energy_j, avg_cpu = self.rapl.measure_energy(duration_seconds)
            return {
                'energy_joules': energy_j,
                'avg_power_watts': energy_j / duration_seconds if duration_seconds > 0 else 0,
                'avg_cpu_percent': avg_cpu,
                'duration_s': duration_seconds,
                'source': 'rapl'
            }
        
        # Fallback to estimation
        if psutil:
            start_time = time.time()
            cpu_samples = []
            sample_interval = min(0.5, duration_seconds / 10)
            
            while time.time() - start_time < duration_seconds:
                cpu_samples.append(psutil.cpu_percent(interval=sample_interval))
            
            avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
            estimated_power = 5.25 + (15.0 - 5.25) * (avg_cpu / 100) ** 1.2
            energy_j = estimated_power * duration_seconds
            
            return {
                'energy_joules': energy_j,
                'avg_power_watts': estimated_power,
                'avg_cpu_percent': avg_cpu,
                'duration_s': duration_seconds,
                'source': 'estimate'
            }
        
        return {
            'energy_joules': 0.0,
            'avg_power_watts': 0.0,
            'avg_cpu_percent': 0.0,
            'duration_s': duration_seconds,
            'source': 'unavailable'
        }


# Convenience functions
_monitor: Optional[PowerMonitor] = None

def get_power_monitor() -> PowerMonitor:
    """Get singleton power monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PowerMonitor()
    return _monitor


def get_current_power() -> float:
    """Get current power in Watts (convenience function)."""
    result = get_power_monitor().get_current_power()
    return result.get('power_watts', 0.0)


def measure_energy(duration_seconds: float) -> float:
    """Measure energy in Joules over a period (convenience function)."""
    result = get_power_monitor().measure_energy(duration_seconds)
    return result.get('energy_joules', 0.0)


if __name__ == "__main__":
    # Test the power monitor
    logging.basicConfig(level=logging.INFO)
    
    print("=== Power Monitor Test ===\n")
    
    monitor = PowerMonitor()
    
    if monitor.rapl.is_available():
        print(f"RAPL domains available: {monitor.rapl.get_available_domains()}")
    else:
        print("RAPL not available, using estimation")
    
    print("\n--- Current Power ---")
    power = monitor.get_current_power(sample_duration_s=0.5)
    print(f"Power: {power['power_watts']:.2f} W")
    print(f"CPU: {power['cpu_percent']:.1f}%")
    print(f"Source: {power['source']}")
    
    print("\n--- Energy Measurement (3 seconds) ---")
    energy = monitor.measure_energy(3.0)
    print(f"Energy: {energy['energy_joules']:.2f} J")
    print(f"Avg Power: {energy['avg_power_watts']:.2f} W")
    print(f"Avg CPU: {energy['avg_cpu_percent']:.1f}%")
    print(f"Source: {energy['source']}")
    
    if monitor.rapl.is_available():
        print("\n--- All RAPL Domains ---")
        all_power = monitor.rapl.get_all_domains_power(sample_duration_s=0.5)
        for domain, sample in all_power.items():
            print(f"  {domain}: {sample.power_watts:.2f} W")
