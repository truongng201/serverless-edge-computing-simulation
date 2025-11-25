import logging
import threading
import time

from config import Config, ContainerState
from central_node.api_layer.central_controller import CentralNodeAPIController

class CentralNodeAPIAgent:
    def __init__(self, controller: CentralNodeAPIController):
        self.logger = logging.getLogger(__name__)
        self.controller = controller
        self.container_manager = self.controller.container_manager
        self.cleanup_thread = None
        self.is_cleaning = False
        self.cleanup_interval = Config.CLEANUP_WARM_CONTAINERS_INTERVAL
        
        self.logger.info("Central Node API Agent initialized")
       
    def _cleanup_warm_containers(self, max_warm_time: int = Config.DEFAULT_MAX_WARM_TIME):
        """Clean up expired warm containers"""
        try:
            current_time = time.time()
            dead_containers = self.container_manager.list_containers(ContainerState.DEAD)

            cleaned_count = 0
            for container in dead_containers:
                if container.started_at and (current_time - container.started_at) > max_warm_time:
                    try:
                        self.container_manager.remove_container(container.container_id)
                        self.logger.info(f"Cleaned up dead container: {container.container_id[:12]}")
                        cleaned_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to remove container {container.container_id[:12]}: {e}")
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} dead containers")
                
        except Exception as e:
            self.logger.error(f"Error in cleanup_warm_containers: {e}", exc_info=True)
   
    def cleanup_warm_containers_loop(self):
        """Main cleanup loop"""
        self.logger.info("Cleanup warm containers loop started")
        
        while self.is_cleaning:
            try:
                loop_start = time.time()
                self._cleanup_warm_containers()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.cleanup_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Cleanup took {elapsed:.2f}s, "
                        f"longer than interval {self.cleanup_interval}s"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                time.sleep(self.cleanup_interval)
        
        self.logger.info("Cleanup warm containers loop stopped")

    def start_cleanup_containers(self):
        """Start cleanup thread"""
        if self.is_cleaning:
            self.logger.warning("Cleanup is already running")
            return
            
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(
            target=self.cleanup_warm_containers_loop,
            name="CentralAgent-Cleanup"
        )
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup thread started")
        
    def stop_cleanup_containers(self):
        """Stop cleanup thread"""
        self.logger.info("Stopping cleanup thread...")
        self.is_cleaning = False
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
            
        self.logger.info("Cleanup thread stopped")

    def start_all_tasks(self):
        """Start all background tasks"""
        self.start_cleanup_containers()
    
    def stop_all_tasks(self):
        """Stop all background tasks"""
        self.stop_cleanup_containers()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.stop_all_tasks()
        except:
            pass