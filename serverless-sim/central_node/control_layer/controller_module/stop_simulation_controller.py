from central_node.control_layer.scheduler_module.scheduler import Scheduler

from shared import InvalidDataException

class StopSimulationController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
    
    def _stop_simulation(self):
        if not self.scheduler.simulation:
            raise InvalidDataException("Simulation is already stopped")
        
        self.scheduler.stop_simulation()

    def execute(self):
        self._stop_simulation()