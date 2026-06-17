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

        # Add energy consumption metrics. The energy model carries its own
        # `warm_count` (= warm + unknown, for power estimation) and
        # `cold_start_count`; those must NOT clobber the authoritative
        # request-status counts from the turnaround breakdown (otherwise
        # warm_count would include unknowns and disagree with warm_rate).
        energy_metrics = self.scheduler.calculate_energy_consumption(timestep_duration_s=1.0)
        for k in ("warm_count", "cold_count", "unknown_count", "cold_start_count"):
            energy_metrics.pop(k, None)
        self.response.update(energy_metrics)

        return self.response
