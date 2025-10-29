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
        self.dataset_list = {
            "Dataset1": "DACT",
            "Dataset2": "Random generated"
        }
    
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
        
    def get_random_generated_data(self, step_id, num_items = 1000) -> List[Dict[str, Any]]:
        if self.random_generated_data is None:
           self._load_random_generated_data(num_items)
        return self.random_generated_data.get_data_by_step(step_id)