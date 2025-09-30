from typing import Dict, Any
import random
from shared import StandardResponse


class GetPerformanceMetricsController:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.response = []

    def execute(self) -> Dict[str, Any]:
        """
        Get current performance metrics including objective function values
        Returns total turnaround time, migration costs, cold start penalties
        """
        try:
            # Get current performance summary
            performance_summary = self.scheduler.get_performance_summary_for_frontend()
            
            # Get detailed objective function breakdown
            objective_function = self.scheduler.calculate_total_objective_function()
            
            # Get detailed cloudlet metrics
            detailed_metrics = self.scheduler.get_detailed_assignment_metrics()
            
            response_data = {
                "performance_summary": performance_summary,
                "objective_function": objective_function,
                "detailed_cloudlet_metrics": detailed_metrics,
                "algorithm_info": {
                    "current_algorithm": self.scheduler.get_assignment_algorithm(),
                    "available_algorithms": self.scheduler.get_all_assignment_algorithms()
                }
            }
            
            return StandardResponse.success(
                message="Performance metrics retrieved successfully",
                data=response_data
            )
            
        except Exception as e:
            return StandardResponse.error(f"Error retrieving performance metrics: {str(e)}")


class CompareAlgorithmsController:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        
    def execute(self, user_location: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Compare performance of greedy vs CVX algorithms
        Optionally test assignment decision for a new user location
        """
        try:
            comparison_results = self.scheduler.compare_algorithms_performance(user_location)
            
            return StandardResponse.success(
                message="Algorithm comparison completed successfully",
                data=comparison_results
            )
            
        except Exception as e:
            return StandardResponse.error(f"Error comparing algorithms: {str(e)}")


class GetAlgorithmPerformanceDiffController:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        
    def execute(self) -> Dict[str, Any]:
        """
        Get performance difference between current algorithm and theoretical optimal
        """
        try:
            current_objective = self.scheduler.calculate_total_objective_function()
            
            # Store current algorithm
            original_algorithm = self.scheduler.assignment_algorithm
            
            # Get metrics for both algorithms with current assignments
            performance_data = {
                "current_algorithm": original_algorithm.value,
                "current_performance": current_objective,
                "performance_breakdown": {
                    "total_cost": current_objective["total_cost"],
                    "turnaround_time_component": current_objective["total_turnaround_time"],
                    "migration_cost_component": current_objective["total_migration_cost"], 
                    "cold_start_penalty_component": current_objective["total_cold_start_penalty"]
                },
                "efficiency_metrics": {
                    "cost_per_user": current_objective["total_cost"] / max(1, current_objective["num_users"]),
                    "avg_turnaround_time": current_objective["total_turnaround_time"] / max(1, current_objective["num_users"]),
                    "resource_utilization": self.scheduler.get_detailed_assignment_metrics()
                }
            }
            
            return StandardResponse.success(
                message="Algorithm performance analysis completed",
                data=performance_data
            )
            
        except Exception as e:
            return StandardResponse.error(f"Error analyzing algorithm performance: {str(e)}")