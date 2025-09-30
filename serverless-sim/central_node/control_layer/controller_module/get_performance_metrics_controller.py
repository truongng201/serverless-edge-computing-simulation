from typing import Dict, Any
from central_node.control_layer.scheduler_module.scheduler import Scheduler


class GetPerformanceMetricsController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.response = None

    def execute(self) -> Dict[str, Any]:
        performance_summary = self.scheduler.get_performance_summary_for_frontend()
        
        # Get detailed objective function breakdown
        objective_function = self.scheduler.calculate_total_objective_function()
        
        self.response = {
            "performance_summary": performance_summary,
            "objective_function": objective_function,
            "algorithm_info": {
                "current_algorithm": self.scheduler.get_assignment_algorithm(),
            }
        }

        return self.response
