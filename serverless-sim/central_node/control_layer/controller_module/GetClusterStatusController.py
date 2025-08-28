from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.api_layer.central_controller import CentralNodeAPIController


class GetClusterStatusController:
    def __init__(self, scheduler: Scheduler, central_node_api_controller: CentralNodeAPIController):
        self.scheduler = scheduler
        self.central_node_api_controller = central_node_api_controller
        self.response = {
            "central_node": {},
            "cluster_info": {}
        }

    def _get_cluster_status(self):
        scheduler_status = self.scheduler.get_cluster_status()
        central_node_status = self.central_node_api_controller.get_central_node_status()
        central_node_status["location"] = self.scheduler.get_central_node_info().get("location", {"x": 0.0, "y": 0.0})
        central_node_status["coverage"] = self.scheduler.get_central_node_info().get("coverage", 0)
        central_node_status = self.central_node_api_controller.get_central_node_status()
        self.response["central_node"] = central_node_status
        self.response["cluster_info"] = scheduler_status

    def execute(self):
        self._get_cluster_status()
        return self.response

