import logging
from typing import Dict, Any, List, Optional

from .dact_data_loader import DactDataLoader
from .random_generated_data_loader import RandomGeneratedDataLoader

class DataManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dact_loader = None
        self.highd_loader = None
        self.random_generated_data = None
        self.dataset_info = [
            {
               "name": "none",
               "ui_name": "None (add user in frontend)" 
            },
            {
               "name": "dact",
               "ui_name": "DACT Sample"
            },
            {
               "name": "random_generated",
               "ui_name": "Random Generated Data"
            },
            {
                "name": "taxiD",
                "ui_name": "TaxiD"
            },
            {
                "name": "taxiD_Replay",
                "ui_name": "TaxiD Replay"
            },
        ]
        
    def get_dataset_info(self):
        return self.dataset_info
    
    def _load_dact_data(self, data_path: str = None):
        self.dact_loader = DactDataLoader(data_path)
        self.logger.info(f"DACT data loaded with {len(self.dact_loader)} trips")
        
    def _load_random_generated_data(self, num_items):
        self.random_generated_data = RandomGeneratedDataLoader(num_items)
        self.logger.info(f"Random generated data loaded with {num_items} items")
        
    def get_dact_data_by_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        if self.dact_loader is None:
            self._load_dact_data()
        return self.dact_loader.get_data_by_step(step_id)
        
    def get_random_generated_data(self, step_id, num_items = 100) -> List[Dict[str, Any]]:
        if self.random_generated_data is None:
            self._load_random_generated_data(num_items)
        if self.random_generated_data and self.random_generated_data.num_items != num_items:
            self._load_random_generated_data(num_items)       
        return self.random_generated_data.get_data_by_step(step_id)
