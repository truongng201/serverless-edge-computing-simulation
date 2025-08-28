class StopSimulationController:
    def __init__(self, scheduler):
        self.scheduler = scheduler

    def _stop_simulation(self):
        self.scheduler.stop_simulation()

    def execute(self):
        self._stop_simulation()        