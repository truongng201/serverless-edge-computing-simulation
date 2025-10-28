import logging
from typing import Dict, Any, List, Optional

from .dact_data_loader import DactDataLoader
from .vehicle_data_loader import VehicleDataLoader
from .highd_data_loader import HighDDataLoader
from .random_generated_data_loader import RandomGeneratedDataLoader

class DataManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vehicle_loader = None
        self.dact_loader = None
        self.highd_loader = None
        self.random_generated_data = None
    
    def _load_vehicle_data(self, data_path: str = None):
        self.vehicle_loader = VehicleDataLoader(data_path)
        self.logger.info(f"Vehicle data loaded with {len(self.vehicle_loader)} records")
        
    def _load_dact_data(self, data_path: str = None):
        self.dact_loader = DactDataLoader(data_path)
        self.logger.info(f"DACT data loaded with {len(self.dact_loader)} trips")
        
    def _load_highd_data(self, data_path: str = None):
        self.highd_loader = HighDDataLoader(data_path)
        self.logger.info(f"HighD data loaded with {len(self.highd_loader)} vehicles")

    def _load_random_generated_data(self, num_items):
        self.random_generated_data = RandomGeneratedDataLoader(num_items)
        self.logger.info(f"Random generated data loaded with {num_items} items")
        
    def get_vehicle_data_by_timestep(self, timestep: float) -> Optional[Dict[str, Any]]:
        if self.vehicle_loader is None:
            self._load_vehicle_data()
        return self.vehicle_loader.get_data_by_timestep(timestep)
        
    def get_dact_data_by_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        if self.dact_loader is None:
            self._load_dact_data()
        return self.dact_loader.get_data_by_step(step_id)
        
    def get_highd_data_by_frame(self, frame: int) -> Optional[Dict[str, Any]]:
        if self.highd_loader is None:
            self._load_highd_data()
        return self.highd_loader.get_data_by_frame(frame)

    def get_random_generated_data(self, step_id, num_items = 1000) -> List[Dict[str, Any]]:
       if self.random_generated_data is None:
           self._load_random_generated_data(num_items)
       return self.random_generated_data.get_data_by_step(step_id)