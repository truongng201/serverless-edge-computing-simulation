from typing import Dict, Any
from central_node.control_layer.scheduler_module.scheduler import Scheduler


class GetPerformanceMetricsController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.response = None

    def execute(self) -> Dict[str, Any]:
        total_turnaround_time = self.scheduler.calculate_total_turnaround_time()
        
        self.response = {
            "total_turnaround_time": total_turnaround_time
        }

        return self.response
