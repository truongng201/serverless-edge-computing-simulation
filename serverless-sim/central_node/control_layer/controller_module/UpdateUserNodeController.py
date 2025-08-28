from central_node.control_layer.scheduler_module.scheduler import Scheduler

from shared import InvalidDataException, NotFoundException

class UpdateUserNodeController:
    def __init__(self, scheduler: Scheduler, user_data):
        self.scheduler = scheduler
        self.user_data = user_data
        self._validate_user_data()
        
    def _validate_user_data(self):
        if not self.user_data.get("user_id"):
            raise InvalidDataException("User ID is required")
        if not self.user_data.get("location") or ("x" not in self.user_data.get("location") or "y" not in self.user_data.get("location")):
            raise InvalidDataException("Location is required")
        
    def _update_user_node(self):
        user_id = self.user_data.get("user_id")
        new_location = self.user_data.get("location")

        success = self.scheduler.update_user_node(user_id, new_location)

        if not success:
            raise NotFoundException(f"User node {user_id} not found")

    def execute(self):
        self._update_user_node()