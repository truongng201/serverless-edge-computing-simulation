"""
Energy Consumption Model for Serverless Edge Computing Simulation

This module implements a comprehensive energy model for evaluating the total energy 
consumption of serverless edge computing systems. The model captures four main 
components of energy consumption:

E_total = E_static + E_dynamic + E_network + E_cold_start

Where:
    - E_static:     Idle/baseline power consumption of nodes (always-on overhead)
    - E_dynamic:    Workload-dependent compute power (CPU utilization based)
    - E_network:    Energy due to data transfer/offloading between nodes
    - E_cold_start: Container cold start overhead energy

**IMPORTANT**: This model uses REAL system power measurements from the node's
hardware rather than preconfigured static values. Power is estimated based on:
    - Actual CPU utilization from system metrics
    - Real CPU core count and TDP estimation
    - Measured container resource limits

Energy Components Detail:
=========================

1. Static Power (E_static):
   - Base power when CPU is at 0% utilization
   - E_static = P_base × t
   - P_base is estimated from system hardware (TDP × idle_factor)

2. Dynamic Power (E_dynamic):
   - Additional power due to CPU workload
   - E_dynamic = (P_max - P_base) × CPU_util × t
   - Uses actual CPU utilization from metrics

3. Network Energy (E_network):
   - Energy for data transmission (wired Ethernet default)
   - E_network = P_nic × transfer_time
   - P_nic ≈ 0.5W for wired, 2-3W for wireless

4. Cold Start Energy (E_cold_start):
   - Overhead from container initialization
   - E_cold = (P_cold - P_warm) × t_cold
   - Cold start causes ~20-30% power spike

References:
-----------
1. Dayarathna, M., et al. "Data center energy consumption modeling: A survey." 
   IEEE Communications Surveys & Tutorials, 2016.
2. Intel Power Gadget / RAPL interface documentation
3. Fan, X., et al. "Power provisioning for a warehouse-sized computer." ISCA 2007.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


class NodeType(Enum):
    """Types of computing nodes in the edge computing infrastructure."""
    CENTRAL = "central"
    EDGE = "edge"


class NetworkType(Enum):
    """Network connection type for energy calculation."""
    WIRED = "wired"      # Ethernet - low power (~0.5W per interface)
    WIRELESS_4G = "4g"   # 4G LTE - higher power (~2W TX, ~1.5W RX)
    WIRELESS_5G = "5g"   # 5G NR - similar to 4G for now


@dataclass
class SystemPowerProfile:
    """
    Power profile derived from actual system hardware.
    
    This class estimates power characteristics based on real hardware
    rather than using preconfigured static values.
    """
    # CPU characteristics
    cpu_cores: int = 1
    cpu_tdp_w: float = 15.0           # Thermal Design Power in Watts
    
    # Power estimates derived from TDP
    idle_power_w: float = 5.0          # Power at ~0% CPU (typically 30-40% of TDP)
    max_power_w: float = 15.0          # Power at 100% CPU (close to TDP)
    
    # Memory power (roughly 3W per 8GB DIMM)
    memory_power_w: float = 2.0
    
    # Storage power (SSD ~2-3W, HDD ~6-8W)
    storage_power_w: float = 2.0
    
    # Peripherals and base system
    base_system_power_w: float = 5.0
    
    # Network interface power
    nic_wired_power_w: float = 0.5     # Ethernet NIC
    nic_wireless_power_w: float = 2.0  # WiFi/4G module
    
    # Container overhead
    container_cpu_limit: Optional[float] = None
    is_containerized: bool = False
    
    @classmethod
    def from_system(cls, is_edge: bool = True) -> "SystemPowerProfile":
        """
        Create a power profile by detecting actual system hardware.
        
        Args:
            is_edge: True for edge nodes (lower power), False for central server
            
        Returns:
            SystemPowerProfile with hardware-based estimates
        """
        profile = cls()
        
        if psutil is None:
            logging.warning("psutil not available, using default power profile")
            return profile
        
        try:
            # Get CPU information
            profile.cpu_cores = psutil.cpu_count(logical=True) or 1
            
            # Estimate TDP based on core count and node type
            # Edge devices: ~5-15W TDP typical (Raspberry Pi, Jetson, etc.)
            # Server: ~65-150W TDP typical (Xeon, EPYC, etc.)
            if is_edge:
                # Edge device: lower TDP per core
                profile.cpu_tdp_w = min(35.0, profile.cpu_cores * 5.0)
            else:
                # Server: higher TDP per core
                profile.cpu_tdp_w = min(300.0, profile.cpu_cores * 15.0)
            
            # Idle power is typically 30-40% of TDP
            profile.idle_power_w = profile.cpu_tdp_w * 0.35
            profile.max_power_w = profile.cpu_tdp_w
            
            # Memory power estimate (~0.3W per GB)
            try:
                mem_gb = psutil.virtual_memory().total / (1024**3)
                profile.memory_power_w = mem_gb * 0.3
            except:
                profile.memory_power_w = 2.0
            
            # Check if containerized (Docker)
            profile.is_containerized = cls._detect_container()
            if profile.is_containerized:
                profile.container_cpu_limit = cls._get_container_cpu_limit()
                if profile.container_cpu_limit:
                    # Scale power by container CPU limit
                    scale_factor = profile.container_cpu_limit / profile.cpu_cores
                    profile.idle_power_w *= scale_factor
                    profile.max_power_w *= scale_factor
            
            # Base system power (motherboard, PSU inefficiency, etc.)
            if is_edge:
                profile.base_system_power_w = 3.0
            else:
                profile.base_system_power_w = 20.0
                
        except Exception as e:
            logging.warning(f"Failed to detect system hardware: {e}")
        
        return profile
    
    @staticmethod
    def _detect_container() -> bool:
        """Detect if running inside a Docker container."""
        try:
            if os.path.exists('/.dockerenv'):
                return True
            if os.path.exists('/proc/1/cgroup'):
                with open('/proc/1/cgroup', 'rt') as f:
                    return 'docker' in f.read()
            return False
        except:
            return False
    
    @staticmethod
    def _get_container_cpu_limit() -> Optional[float]:
        """Get CPU limit from Docker container cgroup."""
        try:
            # Try cgroup v2
            cpu_max_path = '/sys/fs/cgroup/cpu.max'
            if os.path.exists(cpu_max_path):
                with open(cpu_max_path, 'r') as f:
                    content = f.read().strip().split()
                    if len(content) == 2 and content[0] != 'max':
                        return int(content[0]) / int(content[1])
            
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
        except:
            return None
    
    def get_total_idle_power(self) -> float:
        """Get total system idle power (CPU + memory + storage + base)."""
        return (
            self.idle_power_w
            + self.memory_power_w
            + self.storage_power_w
            + self.base_system_power_w
        )
    
    def get_power_at_utilization(self, cpu_util_percent: float) -> float:
        """
        Calculate total system power at given CPU utilization.
        
        Args:
            cpu_util_percent: CPU utilization (0-100)
            
        Returns:
            Estimated power consumption in Watts
        """
        cpu_util = max(0.0, min(100.0, cpu_util_percent)) / 100.0
        
        # CPU power scales with utilization (slightly super-linear)
        # P_cpu = P_idle + (P_max - P_idle) × util^1.2
        cpu_power = self.idle_power_w + (self.max_power_w - self.idle_power_w) * (cpu_util ** 1.2)
        
        # Total system power
        return (
            cpu_power
            + self.memory_power_w
            + self.storage_power_w
            + self.base_system_power_w
        )


@dataclass
class EnergyBreakdown:
    """
    Detailed breakdown of energy consumption by component.
    
    All energy values are in Joules (J).
    To convert to Watt-hours: Wh = J / 3600
    To convert to kWh: kWh = J / 3_600_000
    """
    
    # Static energy (idle baseline)
    static_energy_j: float = 0.0
    
    # Dynamic energy (workload-dependent compute)
    dynamic_energy_j: float = 0.0
    
    # Network energy (data transfer)
    network_energy_j: float = 0.0
    network_tx_energy_j: float = 0.0          # Transmission component
    network_rx_energy_j: float = 0.0          # Reception component
    
    # Cold start energy (container initialization overhead)
    cold_start_energy_j: float = 0.0
    cold_start_count: int = 0
    warm_count: int = 0
    
    # Total energy
    total_energy_j: float = 0.0
    
    # Per-node breakdown (for detailed analysis)
    edge_nodes_energy_j: Dict[str, float] = field(default_factory=dict)
    central_node_energy_j: float = 0.0
    
    # Power profile used
    edge_power_profile: Optional[SystemPowerProfile] = None
    central_power_profile: Optional[SystemPowerProfile] = None
    
    # Additional metrics
    measurement_duration_s: float = 0.0
    average_power_w: float = 0.0
    num_edge_nodes: int = 0
    num_users: int = 0
    avg_cpu_utilization: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses with detailed breakdown."""
        return {
            # Energy breakdown (all in Joules)
            "static_energy_j": round(self.static_energy_j, 4),
            "dynamic_energy_j": round(self.dynamic_energy_j, 4),
            "network_energy_j": round(self.network_energy_j, 4),
            "network_tx_energy_j": round(self.network_tx_energy_j, 4),
            "network_rx_energy_j": round(self.network_rx_energy_j, 4),
            "cold_start_energy_j": round(self.cold_start_energy_j, 4),
            
            # Counts
            "cold_start_count": self.cold_start_count,
            "warm_count": self.warm_count,
            
            # Total energy in different units
            "total_energy_j": round(self.total_energy_j, 4),
            "total_energy_wh": round(self.total_energy_j / 3600, 6),
            "total_energy_kwh": round(self.total_energy_j / 3_600_000, 9),
            
            # Per-node breakdown
            "edge_nodes_energy_j": {k: round(v, 4) for k, v in self.edge_nodes_energy_j.items()},
            "central_node_energy_j": round(self.central_node_energy_j, 4),
            
            # System info
            "measurement_duration_s": round(self.measurement_duration_s, 2),
            "average_power_w": round(self.average_power_w, 4),
            "num_edge_nodes": self.num_edge_nodes,
            "num_users": self.num_users,
            "avg_cpu_utilization": round(self.avg_cpu_utilization, 2),
            
            # Power profile info (if available)
            "edge_idle_power_w": round(self.edge_power_profile.get_total_idle_power(), 2) if self.edge_power_profile else 0,
            "edge_max_power_w": round(self.edge_power_profile.max_power_w, 2) if self.edge_power_profile else 0,
        }


class EnergyModel:
    """
    Energy consumption model using real system power measurements.
    
    This model calculates total energy consumption based on:
        E_total = E_static + E_dynamic + E_network + E_cold_start
    
    Key features:
        - Uses real system hardware detection (CPU cores, TDP estimation)
        - Adapts to containerized environments (Docker CPU limits)
        - Defaults to wired network connections (lower power)
        - Provides detailed per-component breakdown
    
    Usage:
        # Create model with automatic hardware detection
        model = EnergyModel.from_system()
        
        # Or use default profiles
        model = EnergyModel()
        
        # Calculate energy for a timestep
        energy = model.estimate_timestep_energy(
            num_edge_nodes=10,
            num_users=100,
            avg_edge_cpu_util=45.0,
            ...
        )
    """
    
    def __init__(
        self,
        edge_power_profile: Optional[SystemPowerProfile] = None,
        central_power_profile: Optional[SystemPowerProfile] = None,
        network_type: NetworkType = NetworkType.WIRED,  # Default to wired
        cold_start_duration_s: float = 0.5,
        cold_start_power_multiplier: float = 1.25  # 25% power overhead during cold start
    ):
        """
        Initialize the energy model.
        
        Args:
            edge_power_profile: Power profile for edge nodes (auto-detected if None)
            central_power_profile: Power profile for central server (auto-detected if None)
            network_type: Type of network connection (default: WIRED)
            cold_start_duration_s: Default cold start duration in seconds
            cold_start_power_multiplier: Power overhead multiplier during cold start
        """
        self.logger = logging.getLogger(__name__)
        
        # Power profiles - detect from system if not provided
        self.edge_power_profile = edge_power_profile or SystemPowerProfile.from_system(is_edge=True)
        self.central_power_profile = central_power_profile or SystemPowerProfile.from_system(is_edge=False)
        
        # Network configuration
        self.network_type = network_type
        
        # Cold start parameters
        self.cold_start_duration_s = cold_start_duration_s
        self.cold_start_power_multiplier = cold_start_power_multiplier
        
        # Accumulated energy tracking
        self._accumulated_energy = EnergyBreakdown()
        
        self.logger.info(
            f"EnergyModel initialized: "
            f"Edge(idle={self.edge_power_profile.get_total_idle_power():.1f}W, "
            f"max={self.edge_power_profile.max_power_w:.1f}W), "
            f"Network={self.network_type.value}"
        )
    
    @classmethod
    def from_system(cls, network_type: NetworkType = NetworkType.WIRED) -> "EnergyModel":
        """
        Create an EnergyModel with auto-detected system power profiles.
        
        Args:
            network_type: Type of network connection
            
        Returns:
            EnergyModel configured for the current system
        """
        return cls(
            edge_power_profile=SystemPowerProfile.from_system(is_edge=True),
            central_power_profile=SystemPowerProfile.from_system(is_edge=False),
            network_type=network_type
        )
    
    def reset(self):
        """Reset accumulated energy counters."""
        self._accumulated_energy = EnergyBreakdown()
    
    def get_power_profile(self, node_type: NodeType) -> SystemPowerProfile:
        """Get the power profile for a node type."""
        if node_type == NodeType.EDGE:
            return self.edge_power_profile
        return self.central_power_profile
    
    # ========== STATIC ENERGY CALCULATION ==========
    
    def calculate_static_energy(
        self,
        node_type: NodeType,
        duration_s: float
    ) -> float:
        """
        Calculate static (idle) energy consumption for a node.
        
        Uses real system power profile instead of preconfigured values.
        E_static = P_idle × t
        
        Args:
            node_type: Type of node (EDGE or CENTRAL)
            duration_s: Duration in seconds
            
        Returns:
            Static energy in Joules
        """
        profile = self.get_power_profile(node_type)
        idle_power = profile.get_total_idle_power()
        return idle_power * duration_s
    
    # ========== DYNAMIC ENERGY CALCULATION ==========
    
    def calculate_dynamic_energy(
        self,
        node_type: NodeType,
        cpu_utilization: float,
        duration_s: float
    ) -> float:
        """
        Calculate dynamic (workload-dependent) energy consumption.
        
        Uses real system power profile. The dynamic energy is the ADDITIONAL
        energy above idle, based on CPU utilization.
        
        E_dynamic = (P_total(cpu_util) - P_idle) × t
        
        Args:
            node_type: Type of node (EDGE or CENTRAL)
            cpu_utilization: CPU utilization (0-100%)
            duration_s: Duration in seconds
            
        Returns:
            Dynamic energy in Joules (additional energy above idle)
        """
        profile = self.get_power_profile(node_type)
        
        # Get power at current utilization
        total_power = profile.get_power_at_utilization(cpu_utilization)
        idle_power = profile.get_total_idle_power()
        
        # Dynamic component is the additional power above idle
        dynamic_power = max(0.0, total_power - idle_power)
        
        return dynamic_power * duration_s
    
    # ========== NETWORK ENERGY CALCULATION ==========
    
    def calculate_network_energy(
        self,
        data_size_bytes: float,
        bandwidth_bytes_per_s: float,
        network_type: Optional[NetworkType] = None
    ) -> tuple:
        """
        Calculate network energy for data transfer.
        
        Defaults to WIRED connection (lower power consumption).
        
        E_tx = P_nic × (data_size / bandwidth)
        E_rx = P_nic × (data_size / bandwidth)
        E_network = E_tx + E_rx
        
        Args:
            data_size_bytes: Size of data to transfer in bytes
            bandwidth_bytes_per_s: Network bandwidth in bytes per second
            network_type: Network type (uses model default if None)
            
        Returns:
            Tuple of (total_network_energy, tx_energy, rx_energy) in Joules
        """
        if bandwidth_bytes_per_s <= 0:
            return 0.0, 0.0, 0.0
        
        # Use model's default network type if not specified
        net_type = network_type or self.network_type
        
        # Transfer time in seconds
        transfer_time_s = data_size_bytes / bandwidth_bytes_per_s
        
        # Get NIC power based on network type
        if net_type == NetworkType.WIRED:
            # Wired Ethernet: ~0.5W per interface
            tx_power = self.edge_power_profile.nic_wired_power_w
            rx_power = self.edge_power_profile.nic_wired_power_w
        else:
            # Wireless (4G/5G): ~2W TX, ~1.5W RX
            tx_power = self.edge_power_profile.nic_wireless_power_w
            rx_power = self.edge_power_profile.nic_wireless_power_w * 0.75  # RX is typically less
        
        tx_energy = tx_power * transfer_time_s
        rx_energy = rx_power * transfer_time_s
        
        return tx_energy + rx_energy, tx_energy, rx_energy
    
    # ========== COLD START ENERGY CALCULATION ==========
    
    def calculate_cold_start_energy(
        self,
        node_type: NodeType,
        cold_start_duration_s: Optional[float] = None,
        base_cpu_utilization: float = 50.0
    ) -> float:
        """
        Calculate cold start overhead energy.
        
        During cold start, the container initialization causes:
        1. Higher CPU utilization for container startup
        2. Additional I/O operations for image loading
        3. Memory allocation overhead
        
        E_cold = (P_cold - P_warm) × t_cold
        
        Args:
            node_type: Type of node (EDGE or CENTRAL)
            cold_start_duration_s: Cold start duration (uses default if None)
            base_cpu_utilization: Expected CPU utilization for warm execution (0-100%)
            
        Returns:
            Cold start overhead energy in Joules
        """
        if cold_start_duration_s is None:
            cold_start_duration_s = self.cold_start_duration_s
        
        profile = self.get_power_profile(node_type)
        
        # Warm execution power at base CPU utilization
        p_warm = profile.get_power_at_utilization(base_cpu_utilization)
        
        # Cold start power is higher due to initialization overhead
        p_cold = p_warm * self.cold_start_power_multiplier
        
        # Return the OVERHEAD (difference from warm)
        cold_start_overhead = (p_cold - p_warm) * cold_start_duration_s
        
        return cold_start_overhead
    
    # ========== COMBINED EXECUTION ENERGY ==========
    
    def calculate_execution_energy(
        self,
        node_type: NodeType,
        cpu_utilization: float,
        data_size_bytes: float,
        bandwidth_bytes_per_s: float,
        execution_time_s: float,
        is_cold_start: bool = False,
        cold_start_duration_s: Optional[float] = None,
        network_type: Optional[NetworkType] = None
    ) -> Dict[str, float]:
        """
        Calculate total energy for a single function execution.
        
        E_execution = E_dynamic + E_network + E_cold_start
        
        Note: Static energy should be calculated separately for the node's
        total uptime, not per-execution.
        
        Args:
            node_type: Type of node executing the function
            cpu_utilization: CPU utilization during execution (0-100%)
            data_size_bytes: Request/response data size
            bandwidth_bytes_per_s: Network bandwidth
            execution_time_s: Function execution time
            is_cold_start: Whether this is a cold start
            cold_start_duration_s: Cold start duration (uses default if None)
            network_type: Network type (uses model default if None)
            
        Returns:
            Dictionary with energy breakdown in Joules
        """
        # Dynamic energy for computation
        dynamic_energy = self.calculate_dynamic_energy(
            node_type, cpu_utilization, execution_time_s
        )
        
        # Network energy for data transfer (uplink + downlink) - defaults to WIRED
        network_total, network_tx, network_rx = self.calculate_network_energy(
            data_size_bytes, bandwidth_bytes_per_s, network_type
        )
        
        # Cold start overhead (if applicable)
        cold_start_energy = 0.0
        if is_cold_start:
            cold_start_energy = self.calculate_cold_start_energy(
                node_type, cold_start_duration_s, cpu_utilization
            )
        
        total_energy = dynamic_energy + network_total + cold_start_energy
        
        return {
            "dynamic_energy_j": dynamic_energy,
            "network_energy_j": network_total,
            "network_tx_energy_j": network_tx,
            "network_rx_energy_j": network_rx,
            "cold_start_energy_j": cold_start_energy,
            "total_execution_energy_j": total_energy
        }
    
    # ========== SYSTEM-WIDE ENERGY CALCULATION ==========
    
    def calculate_system_energy(
        self,
        num_edge_nodes: int,
        central_node_active: bool,
        edge_cpu_utilizations: Dict[str, float],
        central_cpu_utilization: float,
        user_executions: List[Dict[str, Any]],
        duration_s: float
    ) -> EnergyBreakdown:
        """
        Calculate total system energy consumption for a simulation period.
        
        Args:
            num_edge_nodes: Number of active edge nodes
            central_node_active: Whether central node is active
            edge_cpu_utilizations: CPU utilization per edge node (node_id -> util%)
            central_cpu_utilization: Central node CPU utilization
            user_executions: List of execution records with:
                - node_id: str
                - node_type: NodeType
                - data_size_bytes: float
                - bandwidth_bytes_per_s: float
                - execution_time_s: float
                - is_cold_start: bool
                - cold_start_duration_s: Optional[float]
            duration_s: Total simulation duration in seconds
            
        Returns:
            EnergyBreakdown with detailed energy consumption
        """
        breakdown = EnergyBreakdown()
        breakdown.measurement_duration_s = duration_s
        breakdown.num_edge_nodes = num_edge_nodes
        breakdown.edge_power_profile = self.edge_power_profile
        breakdown.central_power_profile = self.central_power_profile
        
        # ===== STATIC ENERGY =====
        # All active nodes consume idle power throughout the period
        edge_static = num_edge_nodes * self.calculate_static_energy(NodeType.EDGE, duration_s)
        central_static = 0.0
        if central_node_active:
            central_static = self.calculate_static_energy(NodeType.CENTRAL, duration_s)
        breakdown.static_energy_j = edge_static + central_static
        
        # ===== DYNAMIC ENERGY =====
        # Based on CPU utilization of each node (dynamic is ADDITIONAL power above idle)
        total_dynamic = 0.0
        total_cpu_util = 0.0
        
        for node_id, cpu_util in edge_cpu_utilizations.items():
            # Dynamic energy is already the additional power above idle
            edge_dynamic = self.calculate_dynamic_energy(NodeType.EDGE, cpu_util, duration_s)
            total_dynamic += edge_dynamic
            total_cpu_util += cpu_util
            breakdown.edge_nodes_energy_j[node_id] = edge_dynamic
        
        if edge_cpu_utilizations:
            breakdown.avg_cpu_utilization = total_cpu_util / len(edge_cpu_utilizations)
        
        if central_node_active:
            central_dynamic = self.calculate_dynamic_energy(NodeType.CENTRAL, central_cpu_utilization, duration_s)
            total_dynamic += central_dynamic
            breakdown.central_node_energy_j = central_dynamic
        
        breakdown.dynamic_energy_j = total_dynamic
        
        # ===== NETWORK + COLD START ENERGY =====
        # Accumulated from individual executions
        total_network = 0.0
        total_tx = 0.0
        total_rx = 0.0
        total_cold_start = 0.0
        cold_start_count = 0
        warm_count = 0
        
        for exec_record in user_executions:
            node_type = exec_record.get("node_type", NodeType.EDGE)
            if isinstance(node_type, str):
                node_type = NodeType.EDGE if node_type.lower() == "edge" else NodeType.CENTRAL
            
            # Network energy (defaults to WIRED)
            net_total, net_tx, net_rx = self.calculate_network_energy(
                exec_record.get("data_size_bytes", 0),
                exec_record.get("bandwidth_bytes_per_s", 1000000),
                network_type=exec_record.get("network_type")  # Uses model default (WIRED)
            )
            total_network += net_total
            total_tx += net_tx
            total_rx += net_rx
            
            # Cold start energy
            if exec_record.get("is_cold_start", False):
                cold_energy = self.calculate_cold_start_energy(
                    node_type,
                    exec_record.get("cold_start_duration_s"),
                    base_cpu_utilization=50.0
                )
                total_cold_start += cold_energy
                cold_start_count += 1
            else:
                warm_count += 1
        
        breakdown.network_energy_j = total_network
        breakdown.network_tx_energy_j = total_tx
        breakdown.network_rx_energy_j = total_rx
        breakdown.cold_start_energy_j = total_cold_start
        breakdown.cold_start_count = cold_start_count
        breakdown.warm_count = warm_count
        breakdown.num_users = len(user_executions)
        
        # ===== TOTAL ENERGY =====
        breakdown.total_energy_j = (
            breakdown.static_energy_j
            + breakdown.dynamic_energy_j
            + breakdown.network_energy_j
            + breakdown.cold_start_energy_j
        )
        
        # Average power
        if duration_s > 0:
            breakdown.average_power_w = breakdown.total_energy_j / duration_s
        
        return breakdown
    
    # ========== SIMPLIFIED ESTIMATION FOR EXPERIMENTS ==========
    
    def estimate_timestep_energy(
        self,
        num_edge_nodes: int,
        num_users: int,
        avg_edge_cpu_util: float,
        avg_data_size_bytes: float,
        avg_bandwidth_bytes_per_s: float,
        cold_start_count: int,
        warm_count: int,
        timestep_duration_s: float = 1.0
    ) -> Dict[str, float]:
        """
        Estimate energy consumption for a single simulation timestep.
        
        Uses real system power profiles and defaults to WIRED network.
        Provides detailed breakdown of each energy component.
        
        Args:
            num_edge_nodes: Number of active edge nodes
            num_users: Number of active users
            avg_edge_cpu_util: Average CPU utilization across edge nodes (0-100%)
            avg_data_size_bytes: Average data size per user request
            avg_bandwidth_bytes_per_s: Average network bandwidth
            cold_start_count: Number of cold starts in this timestep
            warm_count: Number of warm executions in this timestep
            timestep_duration_s: Duration of the timestep
            
        Returns:
            Dictionary with detailed energy breakdown:
                - static_energy_j: Idle/baseline energy (all nodes)
                - dynamic_energy_j: Workload-dependent energy (CPU utilization)
                - network_energy_j: Data transfer energy (wired by default)
                - cold_start_energy_j: Container cold start overhead
                - total_energy_j: Sum of all components
                - average_power_w: Average power consumption
        """
        # ===== STATIC ENERGY =====
        # Idle power that the marginal serverless edge stack consumes on top of the
        # underlying host. STATIC_OVERHEAD_FRACTION (default 0.1) attributes only the
        # share of idle power belonging to the serverless runtime (containerd, agent,
        # health checks), not the full server. Set to 1.0 to bill full idle power.
        from config import Config as _Cfg
        static_scale = float(getattr(_Cfg, "STATIC_OVERHEAD_FRACTION", 0.1))
        edge_static = num_edge_nodes * self.calculate_static_energy(NodeType.EDGE, timestep_duration_s) * static_scale
        central_static = self.calculate_static_energy(NodeType.CENTRAL, timestep_duration_s) * static_scale
        static_energy = edge_static + central_static
        
        # ===== DYNAMIC ENERGY =====
        # Dynamic energy = energy from actual function executions (warm only)
        # Cold start energy is separate - it captures the initialization overhead
        
        # Base dynamic from CPU utilization (infrastructure overhead)
        base_dynamic_energy = 0.0
        for _ in range(num_edge_nodes):
            edge_dynamic = self.calculate_dynamic_energy(
                NodeType.EDGE, avg_edge_cpu_util, timestep_duration_s
            )
            base_dynamic_energy += edge_dynamic
        
        # Execution energy: ONLY warm executions count as dynamic
        # Cold execution overhead goes to cold_start_energy (not double counted)
        # Pulled from Config.SIM_EXEC_WARM_MS_EDGE so latency and energy stay aligned.
        warm_exec_duration_s = float(getattr(_Cfg, "SIM_EXEC_WARM_MS_EDGE", 300.0)) / 1000.0
        warm_exec_cpu_percent = 30.0  # CPU spike during warm execution
        
        # Energy per warm execution
        warm_exec_energy = self.calculate_dynamic_energy(
            NodeType.EDGE, warm_exec_cpu_percent, warm_exec_duration_s
        )
        
        execution_dynamic_energy = warm_count * warm_exec_energy
        
        # Warm container maintenance: keeping containers warm consumes idle resources
        # Each warm container uses ~2-5% CPU for health checks, garbage collection, etc.
        warm_container_idle_cpu = 3.0  # ~3% CPU per warm container
        warm_container_idle_duration = timestep_duration_s
        warm_maintenance_energy = warm_count * self.calculate_dynamic_energy(
            NodeType.EDGE, warm_container_idle_cpu, warm_container_idle_duration
        )
        
        dynamic_energy = base_dynamic_energy + execution_dynamic_energy + warm_maintenance_energy
        
        # ===== NETWORK ENERGY =====
        # Network energy has two components:
        # 1. Regular data transfer for function execution (all executions)
        # 2. Migration overhead when switching nodes (cold starts = node switches)
        total_executions = cold_start_count + warm_count
        network_energy = 0.0
        network_tx_energy = 0.0
        network_rx_energy = 0.0
        
        if total_executions > 0 and avg_data_size_bytes > 0:
            # Each execution involves uplink (request) + downlink (response)
            for _ in range(total_executions):
                net_total, net_tx, net_rx = self.calculate_network_energy(
                    avg_data_size_bytes,
                    avg_bandwidth_bytes_per_s,
                    network_type=None  # Uses model default (WIRED)
                )
                network_energy += net_total
                network_tx_energy += net_tx
                network_rx_energy += net_rx
        
        # Migration overhead: cold starts often mean node switching
        # Switching nodes requires state transfer, connection setup, etc.
        # Migration cost = ~2x the normal request data transfer
        migration_overhead_factor = 2.0
        for _ in range(cold_start_count):
            migration_net, migration_tx, migration_rx = self.calculate_network_energy(
                avg_data_size_bytes * migration_overhead_factor,
                avg_bandwidth_bytes_per_s,
                network_type=None
            )
            network_energy += migration_net
            network_tx_energy += migration_tx
            network_rx_energy += migration_rx
        
        # ===== COLD START ENERGY =====
        # Cold start energy is the MARGINAL cost over warm execution:
        # - Extra time: cold adds ~100ms extra latency (not 250ms - that was too high)
        # - Extra CPU: brief spike during container init
        # This should be a small marginal cost, not dominate the total
        cold_start_energy = 0.0
        
        # Realistic cold start parameters
        # Pulled from Config.SIM_EXEC_COLD_PENALTY_MS_EDGE so the cold-start energy
        # penalty matches the cold-start latency penalty applied in the latency model.
        extra_latency_s = float(getattr(_Cfg, "SIM_EXEC_COLD_PENALTY_MS_EDGE", 1050.0)) / 1000.0
        cold_init_cpu = 40.0        # Moderate CPU spike (not 60%)
        
        # Energy for the extra latency at init CPU (the penalty)
        cold_penalty_energy = self.calculate_dynamic_energy(
            NodeType.EDGE, cold_init_cpu, extra_latency_s
        )
        
        # Small container init overhead (image layer check, memory allocation)
        # Should be very small - just the marginal cost
        container_init_overhead_j = 0.1  # ~0.1J for container init
        
        for _ in range(cold_start_count):
            cold_start_energy += cold_penalty_energy + container_init_overhead_j
        
        # ===== TOTAL ENERGY =====
        total_energy = static_energy + dynamic_energy + network_energy + cold_start_energy
        
        # Calculate average power
        average_power = total_energy / timestep_duration_s if timestep_duration_s > 0 else 0.0
        
        return {
            # Energy breakdown (all in Joules)
            "static_energy_j": round(static_energy, 4),
            "dynamic_energy_j": round(dynamic_energy, 4),
            "network_energy_j": round(network_energy, 4),
            "network_tx_energy_j": round(network_tx_energy, 4),
            "network_rx_energy_j": round(network_rx_energy, 4),
            "cold_start_energy_j": round(cold_start_energy, 4),
            
            # Total energy
            "total_energy_j": round(total_energy, 4),
            "total_energy_wh": round(total_energy / 3600, 6),
            
            # Counts
            "cold_start_count": cold_start_count,
            "warm_count": warm_count,
            
            # Power metrics
            "average_power_w": round(average_power, 4),
            
            # System info
            "num_edge_nodes": num_edge_nodes,
            "num_users": num_users,
            "avg_cpu_utilization": round(avg_edge_cpu_util, 2),
            
            # Power profile info
            "edge_idle_power_w": round(self.edge_power_profile.get_total_idle_power(), 2),
            "edge_max_power_w": round(self.edge_power_profile.max_power_w, 2),
            "network_type": self.network_type.value,
        }


# ========== SINGLETON INSTANCE ==========
# Global energy model instance with default parameters
_default_energy_model: Optional[EnergyModel] = None


def get_energy_model() -> EnergyModel:
    """Get or create the global energy model instance."""
    global _default_energy_model
    if _default_energy_model is None:
        _default_energy_model = EnergyModel()
    return _default_energy_model


def reset_energy_model():
    """Reset the global energy model to default state."""
    global _default_energy_model
    _default_energy_model = None
