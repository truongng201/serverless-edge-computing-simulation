import logging
import threading
import time

from central_node.api_layer.central_controller import CentralNodeAPIController

from config import Config, ContainerState

class CentralNodeAPIAgent:
    def __init__(self, controller: CentralNodeAPIController):
        self.logger = logging.getLogger(__name__)
        self.controller = controller
        
        # Initialize managers
        self.container_manager = self.controller.container_manager
        
        # Cleanup warm containers
        self.cleanup_thread = None
        self.is_cleaning = False
        self.cleanup_interval = Config.CLEANUP_WARM_CONTAINERS_INTERVAL
        
        self.logger.info("Central Node API Agent initialized")
       

    def _cleanup_warm_containers(self, max_warm_time: int = Config.DEFAULT_MAX_WARM_TIME) -> None:
        current_time = time.time()
        warm_containers = self.container_manager.list_containers(ContainerState.WARM)

        for container in warm_containers:
            if container.stopped_at and (current_time - container.stopped_at) > max_warm_time:
                self.container_manager.remove_container(container.container_id)
                self.logger.info(f"Cleaned up warm container: {container.container_id[:12]}")
   
    def cleanup_warm_containers_loop(self):
        while True:
            try:
                self._cleanup_warm_containers()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.cleanup_interval)

    def start_cleanup_containers(self):
        if self.is_cleaning:
            return
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_warm_containers_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup thread started")
        
    def stop_cleanup_containers(self):
        self.is_cleaning = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        self.logger.info("Cleanup thread stopped")