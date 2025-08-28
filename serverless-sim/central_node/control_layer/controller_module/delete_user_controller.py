from central_node.control_layer.scheduler_module.scheduler import Scheduler

from shared import NotFoundException, InvalidDataException

class DeleteUserController:
    def __init__(self, scheduler: Scheduler, user_id: str):
        self.scheduler = scheduler
        self.user_id = user_id  
        self._validate_user()

    def _validate_user(self):
        if not self.user_id:
            raise InvalidDataException("User ID is required")
        if self.user_id not in self.scheduler.user_nodes:
            raise NotFoundException(f"User {self.user_id} not found")

    def _delete_all_users(self):
        del self.scheduler.user_nodes[self.user_id]

    def execute(self):
        self._delete_all_users()