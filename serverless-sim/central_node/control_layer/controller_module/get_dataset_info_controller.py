from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.helper_module.data_manager import DataManager

class GetDatasetListController:
    def __init__(self, scheduler: Scheduler, data_manager: DataManager,):
        self.data_manager = data_manager
        self.scheduler = scheduler
        self.response = {
            "current_dataset": None,
            "dataset_list": [],
            "sample_size": 0
        }
        
    def get_dataset_detail_information(self):
        self.response["dataset_list"] = self.data_manager.get_dataset_info()
        self.response["current_dataset"] = self.scheduler.get_current_dataset()
        self.response["sample_size"] = self.scheduler.get_sample_size()

    def execute(self):
        self.get_dataset_detail_information()
        return self.response

