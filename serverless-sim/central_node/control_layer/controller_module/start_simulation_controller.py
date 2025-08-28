from central_node.control_layer.scheduler_module.scheduler import Scheduler

from shared import InvalidDataException
class StartSimulationController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
    
    def _start_simulation(self):
        if self.scheduler.simulation:
            raise InvalidDataException("Simulation is already running")
        
        self.scheduler.start_simulation()

    def execute(self):
        self._start_simulation()