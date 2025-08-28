from central_node.api_layer import CentralNodeAPIController

from shared import BadRequestException

class ExecuteFunctionController:
    def __init__(self, central_node_api_controller: CentralNodeAPIController, request_data):
        self.central_node_api_controller = central_node_api_controller
        self.request_data = request_data
        self.response = None
        
    def _execute_function(self):
        self.response = self.central_node_api_controller.execute_function(self.request_data)
        if self.response.get("status") != "success":
            raise BadRequestException("Failed to execute function")

    def execute(self):
        self._execute_function()
        return self.response
