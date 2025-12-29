from typing import Dict, Any
from central_node.control_layer.scheduler_module.scheduler import Scheduler


class GetPerformanceMetricsController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.response = None

    def execute(self) -> Dict[str, Any]:
        # Keep backward-compatible key `total_turnaround_time`, but include
        # warm/cold breakdown for experiment analysis.
        breakdown = self.scheduler.calculate_turnaround_time_breakdown()
        self.response = dict(breakdown)

        return self.response
