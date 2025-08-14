import logging
import threading
from typing import Dict, Any, Optional

from central_node.control_layer.helper_module.data_manager import DataManager


class UIController:
    """
    Handles UI-related requests for the simulation interface.
    Provides legacy compatibility while integrating with the control layer.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_manager = None
        
        # Global variables to manage simulation state
        self.simulation_running = False
        self.step_lock = threading.Lock()
        
        self.logger.info("UI Handler initialized in control layer")
        
    def get_sample_data(self, timestep: float) -> Optional[Dict[str, Any]]:
        """
        Get sample data for a specific timestep from vehicle dataset.
        """
        try:
            self.logger.info(f"Requesting vehicle data for timestep: {timestep}")
            return self.data_manager.get_vehicle_data_by_timestep(timestep)
        except Exception as e:
            self.logger.error(f"Error getting sample data: {e}")
            return None

    def get_dact_sample_data(self, step_id: int) -> Optional[Dict[str, Any]]:
        """
        Get sample data for a specific step from DACT dataset.
        """
        try:
            self.logger.info(f"Requesting DACT data for step: {step_id}")
            return self.data_manager.get_dact_data_by_step(step_id)
        except Exception as e:
            self.logger.error(f"Error getting DACT sample data: {e}")
            return None