import logging
import threading
import time

from config import Config, ContainerState

class CentralNodeAPIAgent:
    def __init__(self, controller):
        self.logger = logging.getLogger(__name__)
        self.controller = controller
        self.container_manager = self.controller.container_manager
        self.cleanup_thread = None
        self.is_cleaning = False
        
        self.logger.info("Central Node API Agent initialized")
       

    def _cleanup_warm_containers(self):
        current_time = time.time()
        warm_containers = self.container_manager.list_containers(ContainerState.WARM)

        for container in warm_containers:
            if container.stopped_at and (current_time - container.stopped_at) > Config.DEFAULT_MAX_WARM_TIME:
                self.container_manager.remove_container(container.container_id)
                self.logger.info(f"Cleaned up warm container: {container.container_id[:12]}")
   
    def cleanup_warm_containers_loop(self):
        while True:
            try:
                self._cleanup_warm_containers()
                time.sleep(Config.CLEANUP_WARM_CONTAINERS_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(Config.CLEANUP_WARM_CONTAINERS_INTERVAL)

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

    def start_all_tasks(self):
        self.start_cleanup_containers()