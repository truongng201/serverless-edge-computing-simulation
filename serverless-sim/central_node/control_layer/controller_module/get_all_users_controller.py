from central_node.control_layer.scheduler_module.scheduler import Scheduler

class GetAllUsersController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        
    def _get_all_users(self):
        pass    
        
    def execute(self):
        self._get_all_users()