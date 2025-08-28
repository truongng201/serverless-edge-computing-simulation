from central_node.control_layer.scheduler_module.scheduler import Scheduler
from shared import InvalidDataException, NotFoundException

class UpdateEdgeNodeController:
    def __init__(self, scheduler: Scheduler, node_data: dict):
        self.scheduler = scheduler
        self.node_data = node_data
        self._validate_node_data()
        
    def _validate_node_data(self):
        if not self.node_data or "node_id" not in self.node_data:
            raise InvalidDataException("Invalid node data")

        if not self.node_data.get("location", None):
            raise InvalidDataException("New location is required")
        
        if self.node_data.get("coverage") and self.node_data["coverage"] <= 0:
            raise InvalidDataException("New coverage must be positive")

    def _update_edge_node(self):
        current_edge_node = self.scheduler.get_edge_node(self.node_data.get("node_id"))
        
        if not current_edge_node:
            raise NotFoundException("Edge node not found")

        current_edge_node.location = self.node_data.get("location", current_edge_node.location)
        current_edge_node.coverage = self.node_data.get("coverage", current_edge_node.coverage)
        self.scheduler.update_edge_node(current_edge_node)
        

    def execute(self):
        self._update_edge_node()