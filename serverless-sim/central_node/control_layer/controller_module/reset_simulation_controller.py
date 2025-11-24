from central_node.control_layer.scheduler_module.scheduler import Scheduler

class ResetSimulationController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler

    def _reset_simulation(self):
        self.scheduler.simulation = False
        self.scheduler.set_current_dataset(None)
        self.scheduler.set_current_step_id(None)
        self.scheduler.delete_all_user()

    def execute(self):
        self._reset_simulation()