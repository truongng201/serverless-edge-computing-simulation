import logging
from typing import Dict, Any
import time

from central_node.control_layer.scheduler_module.scheduler import Scheduler, EdgeNodeInfo
from central_node.control_layer.prediction_module.prediction import WorkloadPredictor
from central_node.control_layer.migration_module.migration import MigrationManager
from central_node.control_layer.metrics_module.global_metrics import GlobalMetricsCollector
from central_node.control_layer.metrics_module.global_metrics import NodeMetrics
from shared_resource_layer.container_manager import ContainerManager
from shared_resource_layer.system_metrics import SystemMetricsCollector


class CentralCoreController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize control layer components
        self.scheduler = Scheduler()
        self.predictor = WorkloadPredictor()
        self.migration_manager = MigrationManager()
        self.metrics_collector = GlobalMetricsCollector()
        self.central_metrics_monitor = SystemMetricsCollector()
        self.container_manager = ContainerManager()
        
        # Start metrics collection and monitoring
        self.metrics_collector.start_collection()
        
        # Initialize with default values, will be updated by get_current_central_metrics()
        self.container_count = 0
        self.active_requests = 0
        self.response_time_avg = 0.0

    def get_current_central_metrics(self) -> NodeMetrics:
        """Get real-time central node metrics"""
        try:
            detailed_metrics = self.central_metrics_monitor.get_detailed_metrics()
            
            return NodeMetrics(
                node_id="central_node",
                timestamp=detailed_metrics.get('timestamp', time.time()),
                cpu_usage=detailed_metrics.get('cpu_usage', 0.0),
                memory_usage=detailed_metrics.get('memory_usage', 0.0),
                network_io=detailed_metrics.get('network_io', {}),
                disk_io=detailed_metrics.get('disk_io', {}),
                container_count=self.container_count,
                active_requests=self.active_requests,
                response_time_avg=self.response_time_avg,
                energy_consumption=detailed_metrics.get('cpu_energy_kwh', 0.0)
            )
        except Exception as e:
            self.logger.error(f"Failed to get central metrics: {e}")
            # Return default metrics if collection fails
            return NodeMetrics(
                node_id="central_node",
                timestamp=time.time(),
                cpu_usage=0.0,
                memory_usage=0.0,
                network_io={},
                disk_io={},
                container_count=self.container_count,
                active_requests=self.active_requests,
                response_time_avg=self.response_time_avg,
                energy_consumption=0.0
            )

    def update_central_node_stats(self, container_count: int = None, active_requests: int = None, response_time_avg: float = None):
        """Update central node dynamic statistics"""
        if container_count is not None:
            self.container_count = container_count
        if active_requests is not None:
            self.active_requests = active_requests
        if response_time_avg is not None:
            self.response_time_avg = response_time_avg

    def schedule_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a request to an edge node"""
        try:
            decision = self.scheduler.schedule_request(request_data)
            
            if not decision:
                return {
                    "success": False,
                    "error": "No available edge nodes",
                    "code": "NO_NODES_AVAILABLE"
                }
                
            return {
                "success": True,
                "target_node": decision.target_node_id,
                "estimated_time": decision.execution_time_estimate,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            self.logger.error(f"Request scheduling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "SCHEDULING_ERROR"
            }
            
    def register_edge_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new edge node"""
        try:
            
            node_info = EdgeNodeInfo(
                node_id=node_data["node_id"],
                endpoint=node_data["endpoint"],
                location=node_data.get("location", {"x": 0.0, "y": 0.0}),
                current_load=0.0,
                available_resources=node_data.get("resources", {}),
                last_heartbeat=time.time()
            )
            
            self.scheduler.register_edge_node(node_info)
            
            return {
                "success": True,
                "message": f"Edge node {node_data['node_id']} registered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Node registration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "REGISTRATION_ERROR"
            }
            
    def update_node_metrics(self, node_id: str, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update metrics from an edge node"""
        try:
            # Update scheduler with basic metrics (this will also clean up dead nodes)
            self.scheduler.update_node_metrics(node_id, metrics_data)
            
            # Add to global metrics collection
            node_metrics = NodeMetrics(
                node_id=node_id,
                timestamp=time.time(),
                cpu_usage=metrics_data.get("cpu_usage", 0.0),
                memory_usage=metrics_data.get("memory_usage", 0.0),
                network_io=metrics_data.get("network_io", {}),
                disk_io=metrics_data.get("disk_io", {}),
                container_count=metrics_data.get("container_count", 0),
                active_requests=metrics_data.get("active_requests", 0),
                response_time_avg=metrics_data.get("response_time_avg", 0.0),
                energy_consumption=metrics_data.get("energy_consumption", 0.0)
            )
            
            self.metrics_collector.add_node_metrics(node_metrics)
            
            # Check if migration is needed
            migration_reason = self.migration_manager.should_migrate_container(
                {"node_id": node_id}, metrics_data
            )
            
            migration_suggested = migration_reason is not None
            
            # Log the heartbeat
            self.logger.debug(f"Received metrics from node {node_id}: CPU={metrics_data.get('cpu_usage', 0):.1f}%, Memory={metrics_data.get('memory_usage', 0):.1f}%")
            
            return {
                "success": True,
                "migration_suggested": migration_suggested,
                "migration_reason": migration_reason.value if migration_reason else None
            }
            
        except Exception as e:
            self.logger.error(f"Metrics update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "METRICS_ERROR"
            }
            
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status including central node metrics"""
        try:
            scheduler_status = self.scheduler.get_cluster_status()
            health_summary = self.metrics_collector.get_cluster_health_summary()
            migration_stats = self.migration_manager.get_migration_stats()
            
            # Get real-time central node metrics
            central_metrics = self.get_current_central_metrics()
            
            return {
                "success": True,
                "cluster_info": scheduler_status,
                "central_node": central_metrics,
                "health": health_summary,
                "migrations": migration_stats,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Cluster status failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "STATUS_ERROR"
            }
            
    def predict_workload(self, node_id: str, horizon_minutes: int = 30) -> Dict[str, Any]:
        """Get workload prediction for a node"""
        try:
            prediction = self.predictor.predict_workload(node_id, horizon_minutes)
            
            if not prediction:
                return {
                    "success": False,
                    "error": "Prediction not available",
                    "code": "PREDICTION_ERROR"
                }
                
            return {
                "success": True,
                "prediction": {
                    "predicted_load": prediction.predicted_load,
                    "confidence_interval": prediction.confidence_interval,
                    "horizon_minutes": prediction.prediction_horizon,
                    "accuracy": prediction.model_accuracy
                }
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "PREDICTION_ERROR"
            }

    def cleanup_dead_nodes(self) -> Dict[str, Any]:
        """Manually trigger cleanup of dead nodes"""
        try:
            # Get status before cleanup
            status_before = self.scheduler.get_cluster_status()
            nodes_before = status_before["total_nodes"]
            
            # Trigger cleanup in scheduler
            self.scheduler._cleanup_dead_nodes()
            
            # Trigger cleanup in metrics collector
            metrics_nodes_removed = self.metrics_collector.cleanup_dead_nodes()
            
            # Get status after cleanup
            status_after = self.scheduler.get_cluster_status()
            nodes_after = status_after["total_nodes"]
            
            removed_count = nodes_before - nodes_after
            
            return {
                "success": True,
                "scheduler_nodes_removed": removed_count,
                "metrics_nodes_removed": metrics_nodes_removed,
                "total_nodes_before": nodes_before,
                "total_nodes_after": nodes_after,
                "healthy_nodes": status_after["healthy_nodes"],
                "unhealthy_nodes": status_after["unhealthy_nodes"]
            }
            
        except Exception as e:
            self.logger.error(f"Dead node cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "CLEANUP_ERROR"
            }
