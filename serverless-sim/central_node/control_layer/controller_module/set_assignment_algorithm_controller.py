from central_node.control_layer.scheduler_module.scheduler import Scheduler
from shared import InvalidDataException

class SetAssignmentAlgorithmController:
    def __init__(self, scheduler: Scheduler, request_data: dict):
        self.scheduler = scheduler
        self.request_data = request_data

    def execute(self):
        algorithm = self.request_data.get('algorithm')
        if not algorithm:
            raise InvalidDataException("Algorithm not provided in request data")
        self.scheduler.set_assignment_algorithm(algorithm)
        return f"Assignment algorithm set to {self.scheduler.get_assignment_algorithm()}"