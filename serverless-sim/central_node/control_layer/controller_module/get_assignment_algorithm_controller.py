from central_node.control_layer.scheduler_module.scheduler import Scheduler

class GetAssignmentAlgorithmController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler

    def execute(self) -> str:
        current_algorithm = self.scheduler.get_assignment_algorithm()
        return {
            "algorithm": current_algorithm
        }