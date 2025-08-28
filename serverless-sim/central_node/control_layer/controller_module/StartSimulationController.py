class StartSimulationController:
    def __init__(self, scheduler):
        self.scheduler = scheduler
    
    
    def _start_simulation(self):
        self.scheduler.start_simulation()

    def execute(self):
        self._start_simulation()