from central_node.control_layer.scheduler_module.scheduler import Scheduler

class GetAllAssignmentAlgorithmsController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler

    def execute(self):
        all_assignment_algorithms = self.scheduler.get_all_assignment_algorithms()
        return {
            "algorithms": all_assignment_algorithms
        }