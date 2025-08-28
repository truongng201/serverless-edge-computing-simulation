import time

from shared import InvalidDataException
from central_node.control_layer.scheduler_module.scheduler import Scheduler, EdgeNodeInfo
from central_node.control_layer.metrics_module.global_metrics import NodeMetrics

class RegisterEdgeNodeController:
    def __init__(self, scheduler: Scheduler, node_data: dict):
        self.scheduler = scheduler
        self.node_data = node_data
        self.node_metrics = None
        self.edge_node_info = None
        self._validate_node_data()

    def _validate_node_data(self):
        if not self.node_data or "node_id" not in self.node_data or "endpoint" not in self.node_data:
            raise InvalidDataException("Invalid node data")
        
        
    def _mapping_node_data(self):
        self.node_metrics = NodeMetrics(
            node_id=self.node_data.get("node_id"),
            cpu_usage=0.0,
            memory_usage=0.0,
            memory_total=0,
            running_container=0,
            warm_container=0,
            active_requests=0,
            total_requests=0,
            response_time_avg=0.0,
            energy_consumption=0.0,
            load_average=[],
            network_io={},
            disk_io={},
            timestamp=0,
            uptime=0
        )
        
        self.edge_node_info = EdgeNodeInfo(
            node_id=self.node_data.get('node_id'),
            endpoint=self.node_data.get("endpoint"),
            location=self.node_data.get("location", {"x": 0.0, "y": 0.0}),
            system_info=self.node_data.get("system_info", {}),
            last_heartbeat=time.time(),
            metrics_info=self.node_metrics,
            coverage=self.node_data.get("coverage", 300.0)
        )
        
    def _register_edge_node(self):
        self.scheduler.register_edge_node(self.edge_node_info)

    def execute(self):
        self._mapping_node_data()
        self._register_edge_node()