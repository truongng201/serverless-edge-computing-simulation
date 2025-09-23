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

        # Execute functions
        self.excute_function_thread = None
        self.is_cleaning = False

        # Cleanup inactive users
        self.cleanup_users_thread = None
        self.is_users_cleaning = False

        # Assignment reassignment loop
        self.assignment_thread = None
        self.is_assignment_running = False

        self.logger.info("Users Agent initialized")

    def _excute_function(self):
        # Snapshot to avoid concurrent modification errors during cleanup
        for user_node in list(self.user_nodes.values()):
            # Execute the function for each user node
            assigned_node = user_node.assigned_node_id
            if not assigned_node:
                continue  # Skip if the assigned node is not valid

            if assigned_node == self.central_node['node_id']:
                try:
                    start = time.time()
                    result = requests.post(f"http://{self.central_node['endpoint']}/api/v1/central/execute", json={"user_id": user_node.user_id})
                    end = time.time()
                    container_status = result.json().get("container_status", "unknown")
                    user_node.latency.computation_delay = (end - start) * 1000 # in ms
                    user_node.latency.container_status = container_status
                    user_node.last_executed = time.time()
                    if result.status_code == 200:
                        self.logger.info(f"Function executed successfully for user node: {user_node.user_id} (central node)")
                    else:
                        self.logger.warning(f"Function execution failed for user node: {user_node.user_id} (central node), status code: {result.status_code}")
                except Exception as e:
                    self.logger.error(f"Error executing function for user node: {user_node.user_id} (central node), error: {e}")
                finally:
                    continue  # Skip to the next user node if assigned to central node

            edge_node = self.edge_nodes.get(user_node.assigned_node_id)
            if edge_node:
                try:
                    start = time.time()
                    result = requests.post(f"http://{edge_node.endpoint}/api/v1/edge/execute", json={"user_id": user_node.user_id})
                    end = time.time()
                    computation_delay = (end - start) * 1000  # in ms
                    container_status = result.json().get("container_status", "unknown")
                    user_node.latency.computation_delay = computation_delay
                    user_node.latency.container_status = container_status
                    user_node.last_executed = time.time()
                    if result.status_code == 200:
                        self.logger.info(f"Function executed successfully for user node: {user_node.user_id}")
                    else:
                        self.logger.warning(f"Function execution failed for user node: {user_node.user_id}, status code: {result.status_code}")
                except Exception as e:
                    self.logger.error(f"Error executing function for user node: {user_node.user_id}, error: {e}")

    def excute_function_loop(self):
        while True:
            try:
                self._excute_function()
                time.sleep(Config.DEFAULT_EXECUTION_TIME_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in execute function loop: {e}")
                time.sleep(Config.DEFAULT_EXECUTION_TIME_INTERVAL)

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
