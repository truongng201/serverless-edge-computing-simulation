from central_node.control_layer.scheduler_module.scheduler import Scheduler

class DeleteAllUsersController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        
    def _delete_all_users(self):
        self.scheduler.user_nodes.clear()

    def execute(self):
        self._delete_all_users()