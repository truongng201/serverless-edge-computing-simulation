from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.metrics_module.global_metrics import NodeMetrics

class UpdateNodeMetricsController:
    def __init__(self, scheduler: Scheduler, node_id: str, node_data: dict):
        self.scheduler = scheduler
        self.node_id = node_id
        self.node_data = node_data
        self.node_metrics = None
        self._validate_node_data()


    def _validate_node_data(self):
        if not self.node_data or not self.node_id or "endpoint" not in self.node_data:
            raise ValueError("Invalid node data")


    def _mapping_node_data(self):
        self.node_metrics = NodeMetrics(
            node_id=self.node_id,
            cpu_usage=self.node_data.get("cpu_usage", 0.0),
            memory_usage=self.node_data.get("memory_usage", 0.0),
            memory_total=self.node_data.get("memory_total", 0),
            running_container=self.node_data.get("running_container", 0),
            warm_container=self.node_data.get("warm_container", 0),
            active_requests=self.node_data.get("active_requests", 0),
            total_requests=self.node_data.get("total_requests", 0),
            response_time_avg=self.node_data.get("response_time_avg", 0.0),
            energy_consumption=self.node_data.get("energy_consumption", 0.0),
            load_average=self.node_data.get("load_average", []),
            network_io=self.node_data.get("network_io", {}),
            disk_io=self.node_data.get("disk_io", {}),
            timestamp=self.node_data.get("timestamp", 0),
            uptime=self.node_data.get("uptime", 0)
        )


    def _update_node_metrics(self):
        self.scheduler.update_node_metrics(
            self.node_id,
            self.node_metrics,
            self.node_data.get("system_info", {}),
            self.node_data.get("endpoint", "")
        )


    def execute(self):
        self._mapping_node_data()
        self._update_node_metrics()