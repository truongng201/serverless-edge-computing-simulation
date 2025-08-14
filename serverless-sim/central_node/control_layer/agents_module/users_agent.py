import logging
import threading
import time
import requests
from central_node.control_layer.scheduler_module.scheduler import Scheduler

from config import Config

class UsersAgent:
    def __init__(self, scheduler: Scheduler):
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler
        self.edge_nodes = self.scheduler.edge_nodes
        self.central_node = self.scheduler.central_node
        self.user_nodes = self.scheduler.user_nodes


        # Cleanup dead nodes
        self.excute_function_thread = None
        self.is_cleaning = False
        self.excute_function_interval = Config.DEFAULT_EXECUTION_TIME_INTERVAL

        self.logger.info("Users Agent initialized")

    def _excute_function(self):
        for user_node in self.user_nodes.values():
            # Execute the function for each user node
            self.logger.info(f"Executing function for user node: {user_node.user_id}")
            if user_node.assigned_node_id:
                # Forward the request to the assigned edge node
                edge_node = self.scheduler.edge_nodes.get(user_node.assigned_node_id)
                if edge_node:
                    try:
                        result = requests.post(f"http://{edge_node.endpoint}/api/v1/edge/execute", json={"user_id": user_node.user_id})
                        if result.status_code == 200:
                            self.logger.info(f"Function executed successfully for user node: {user_node.user_id}")
                        else:
                            self.logger.warning(f"Function execution failed for user node: {user_node.user_id}, status code: {result.status_code}")
                    except Exception as e:
                        self.logger.error(f"Error executing function for user node: {user_node.user_id}, error: {e}")

                central_node = self.scheduler.central_node
                if central_node:
                    try:
                        result = requests.post(f"http://{central_node['endpoint']}/api/v1/central/execute", json={"user_id": user_node.user_id})
                        if result.status_code == 200:
                            self.logger.info(f"Function executed successfully for user node: {user_node.user_id} (central node)")
                        else:
                            self.logger.warning(f"Function execution failed for user node: {user_node.user_id} (central node), status code: {result.status_code}")
                    except Exception as e:
                        self.logger.error(f"Error executing function for user node: {user_node.user_id} (central node), error: {e}")

    def excute_function_loop(self):
        while True:
            try:
                self._excute_function()
                time.sleep(self.excute_function_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.excute_function_interval)

    def start_excute_function_containers(self):
        if self.is_cleaning:
            return
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(target=self.excute_function_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup execute function thread started")
        
    def stop_excute_function_containers(self):
        self.is_cleaning = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        self.logger.info("Cleanup execute function thread stopped")

    def start_all_tasks(self):
        self.start_excute_function_containers()
        
    def stop_all_tasks(self):
        self.stop_excute_function_containers()