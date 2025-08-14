"""
Central Node Control Layer - Global Metrics Collection
Aggregates metrics from all edge nodes and provides cluster-wide analytics
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

@dataclass
class NodeMetrics:
    node_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, float]
    disk_io: Dict[str, float]
    container_count: int
    active_requests: int
    response_time_avg: float
    energy_consumption: float  # kWh

@dataclass
class ClusterMetrics:
    timestamp: float
    total_nodes: int
    healthy_nodes: int
    total_cpu_usage: float
    total_memory_usage: float
    total_containers: int
    total_requests: int
    avg_response_time: float
    total_energy: float
    load_distribution: Dict[str, float]

class GlobalMetricsCollector:
    def __init__(self, collection_interval: int = 10):
        self.logger = logging.getLogger(__name__)
        self.collection_interval = collection_interval
        self.node_metrics: Dict[str, List[NodeMetrics]] = {}
        self.cluster_metrics: List[ClusterMetrics] = []
        self.is_collecting = False
        self.collection_thread = None
        
        # Metrics retention (keep last 24 hours by default)
        self.max_metrics_age = 24 * 60 * 60  # 24 hours in seconds
        
    def start_collection(self):
        """Start metrics collection in background thread"""
        if self.is_collecting:
            return
            
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        self.logger.info("Global metrics collection started")
        
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join()
        self.logger.info("Global metrics collection stopped")
        
    def add_node_metrics(self, metrics: NodeMetrics):
        """Add metrics from an edge node"""
        if metrics.node_id not in self.node_metrics:
            self.node_metrics[metrics.node_id] = []
            
        self.node_metrics[metrics.node_id].append(metrics)
        
        # Clean old metrics
        self._cleanup_old_metrics(metrics.node_id)
        
    def get_latest_node_metrics(self, node_id: str) -> Optional[NodeMetrics]:
        """Get latest metrics for a specific node"""
        if node_id not in self.node_metrics or not self.node_metrics[node_id]:
            return None
        return self.node_metrics[node_id][-1]
        
    def get_node_metrics_history(self, node_id: str, duration_minutes: int = 60) -> List[NodeMetrics]:
        """Get metrics history for a node"""
        if node_id not in self.node_metrics:
            return []
            
        cutoff_time = time.time() - (duration_minutes * 60)
        return [m for m in self.node_metrics[node_id] if m.timestamp >= cutoff_time]
        
    def get_cluster_metrics(self) -> Optional[ClusterMetrics]:
        """Get latest cluster-wide metrics"""
        if not self.cluster_metrics:
            return None
        return self.cluster_metrics[-1]
        
    def get_cluster_metrics_history(self, duration_minutes: int = 60) -> List[ClusterMetrics]:
        """Get cluster metrics history"""
        cutoff_time = time.time() - (duration_minutes * 60)
        return [m for m in self.cluster_metrics if m.timestamp >= cutoff_time]
        
    def _collection_loop(self):
        """Main collection loop"""
        cleanup_counter = 0
        while self.is_collecting:
            try:
                # Collect and aggregate cluster metrics
                cluster_metrics = self._calculate_cluster_metrics()
                if cluster_metrics:
                    self.cluster_metrics.append(cluster_metrics)
                    
                # Clean old cluster metrics
                self._cleanup_old_cluster_metrics()
                
                # Clean up dead nodes every 6 cycles (60 seconds if collection_interval is 10s)
                cleanup_counter += 1
                if cleanup_counter >= 6:
                    self.cleanup_dead_nodes()
                    cleanup_counter = 0
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.collection_interval)
                
    def _calculate_cluster_metrics(self) -> Optional[ClusterMetrics]:
        """Calculate cluster-wide metrics from node metrics"""
        if not self.node_metrics:
            return None
            
        current_time = time.time()
        recent_metrics = {}
        
        # Get most recent metrics from each node
        for node_id, metrics_list in self.node_metrics.items():
            if metrics_list:
                latest_metric = metrics_list[-1]
                # Only include recent metrics (within last 2 minutes)
                if current_time - latest_metric.timestamp <= 120:
                    recent_metrics[node_id] = latest_metric
                    
        if not recent_metrics:
            return None
            
        # Calculate aggregated metrics
        total_nodes = len(self.node_metrics)
        healthy_nodes = len(recent_metrics)
        
        total_cpu = sum(m.cpu_usage for m in recent_metrics.values())
        total_memory = sum(m.memory_usage for m in recent_metrics.values())
        total_containers = sum(m.container_count for m in recent_metrics.values())
        total_requests = sum(m.active_requests for m in recent_metrics.values())
        total_energy = sum(m.energy_consumption for m in recent_metrics.values())
        
        # Calculate average response time (weighted by active requests)
        total_weighted_response_time = sum(
            m.response_time_avg * m.active_requests 
            for m in recent_metrics.values()
        )
        avg_response_time = (
            total_weighted_response_time / total_requests 
            if total_requests > 0 else 0.0
        )
        
        # Calculate load distribution
        load_distribution = {
            node_id: metrics.cpu_usage 
            for node_id, metrics in recent_metrics.items()
        }
        
        return ClusterMetrics(
            timestamp=current_time,
            total_nodes=total_nodes,
            healthy_nodes=healthy_nodes,
            total_cpu_usage=total_cpu / healthy_nodes if healthy_nodes > 0 else 0,
            total_memory_usage=total_memory / healthy_nodes if healthy_nodes > 0 else 0,
            total_containers=total_containers,
            total_requests=total_requests,
            avg_response_time=avg_response_time,
            total_energy=total_energy,
            load_distribution=load_distribution
        )
        
    def _cleanup_old_metrics(self, node_id: str):
        """Remove old metrics for a node"""
        if node_id not in self.node_metrics:
            return
            
        cutoff_time = time.time() - self.max_metrics_age
        self.node_metrics[node_id] = [
            m for m in self.node_metrics[node_id] 
            if m.timestamp >= cutoff_time
        ]
        
    def _cleanup_old_cluster_metrics(self):
        """Remove old cluster metrics"""
        cutoff_time = time.time() - self.max_metrics_age
        self.cluster_metrics = [
            m for m in self.cluster_metrics 
            if m.timestamp >= cutoff_time
        ]
        
    def cleanup_dead_nodes(self):
        """Remove nodes that haven't sent metrics for too long"""
        current_time = time.time()
        dead_nodes = []
        
        for node_id, metrics_list in self.node_metrics.items():
            if not metrics_list:
                dead_nodes.append(node_id)
                continue
                
            latest_metric = max(metrics_list, key=lambda m: m.timestamp)
            if current_time - latest_metric.timestamp > 120:  # 2 minutes timeout
                dead_nodes.append(node_id)
                
        for node_id in dead_nodes:
            self.logger.warning(f"Removing dead node from metrics: {node_id}")
            del self.node_metrics[node_id]
            
        return len(dead_nodes)
        
    def get_node_health_status(self, node_id: str) -> Dict[str, Any]:
        """Get health status for a specific node"""
        latest_metrics = self.get_latest_node_metrics(node_id)
        
        if not latest_metrics:
            return {
                "status": "unknown",
                "last_seen": None,
                "issues": ["No metrics available"]
            }
            
        current_time = time.time()
        last_seen = current_time - latest_metrics.timestamp
        
        issues = []
        status = "healthy"
        
        # Check if node is responsive
        if last_seen > 60:  # More than 1 minute old
            issues.append("Node not responding")
            status = "unhealthy"
            
        # Check resource usage
        if latest_metrics.cpu_usage > 0.9:
            issues.append("High CPU usage")
            if status == "healthy":
                status = "warning"
                
        if latest_metrics.memory_usage > 0.9:
            issues.append("High memory usage")
            if status == "healthy":
                status = "warning"
                
        return {
            "status": status,
            "last_seen": last_seen,
            "cpu_usage": latest_metrics.cpu_usage,
            "memory_usage": latest_metrics.memory_usage,
            "container_count": latest_metrics.container_count,
            "active_requests": latest_metrics.active_requests,
            "issues": issues
        }
        
    def get_cluster_health_summary(self) -> Dict[str, Any]:
        """Get overall cluster health summary"""
        all_nodes = list(self.node_metrics.keys())
        nodes_details = []
       
        for node_id in all_nodes:
            current_health_status = self.get_node_health_status(node_id)
            current_health_status["node_id"] = node_id
            nodes_details.append(current_health_status)

        healthy_count = len([h for h in nodes_details if h["status"] == "healthy"])
        warning_count = len([h for h in nodes_details if h["status"] == "warning"])
        unhealthy_count = len([h for h in nodes_details if h["status"] == "unhealthy"])

        latest_cluster = self.get_cluster_metrics()
        
        return {
            "total_nodes": len(all_nodes),
            "healthy_nodes": healthy_count,
            "warning_nodes": warning_count,
            "unhealthy_nodes": unhealthy_count,
            "cluster_load": latest_cluster.total_cpu_usage if latest_cluster else 0,
            "total_containers": latest_cluster.total_containers if latest_cluster else 0,
            "total_energy": latest_cluster.total_energy if latest_cluster else 0,
            "nodes_details": nodes_details
        }
        
    def export_metrics(self, format_type: str = "json", duration_hours: int = 1) -> str:
        """Export metrics data"""
        duration_seconds = duration_hours * 3600
        cutoff_time = time.time() - duration_seconds
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "duration_hours": duration_hours,
            "node_metrics": {},
            "cluster_metrics": []
        }
        
        # Export node metrics
        for node_id, metrics_list in self.node_metrics.items():
            recent_metrics = [
                asdict(m) for m in metrics_list 
                if m.timestamp >= cutoff_time
            ]
            if recent_metrics:
                export_data["node_metrics"][node_id] = recent_metrics
                
        # Export cluster metrics
        export_data["cluster_metrics"] = [
            asdict(m) for m in self.cluster_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        if format_type == "json":
            return json.dumps(export_data, indent=2)
        else:
            # Could add CSV or other formats here
            return json.dumps(export_data, indent=2)
