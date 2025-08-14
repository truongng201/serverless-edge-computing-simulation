import logging
import threading
import time
import requests
from central_node.control_layer.scheduler_module.scheduler import Scheduler

from config import Config

class SchedulerAgent:
    def __init__(self, scheduler: Scheduler):
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler


        # Cleanup dead nodes
        self.cleanup_dead_nodes_thread = None
        self.is_cleaning = False
        self.cleanup_dead_nodes_interval = Config.CLEANUP_DEAD_NODES_INTERVAL
        self.max_attempts_call = 3
        
        self.logger.info("Scheduler Agent initialized")
        
    def _cleanup_dead_nodes(self):    
        current_time = time.time()
        dead_nodes = []
        
        for node_id, node in self.scheduler.edge_nodes.items():
            # for attempt in range(1, self.max_attempts_call + 1):
            #     try:
            #         result = requests.get(f"http://{node.endpoint}/api/v1/edge/health")
            #         if result.status_code != 200:
            #             raise Exception(f"Node {node_id} is unhealthy, status code: {result.status_code}")
            #         break
            #     except Exception as e:
            #         if attempt == self.max_attempts_call:
            #             dead_nodes.append(node_id)
            if node.last_heartbeat is None or (current_time - node.last_heartbeat) > Config.EDGE_NODE_HEARTBEAT_TIMEOUT:
                dead_nodes.append(node_id)

        for node_id in dead_nodes:
            self.logger.warning(f"Removing dead node: {node_id} (last seen: {current_time - self.scheduler.edge_nodes[node_id].last_heartbeat:.1f}s ago)")
            del self.scheduler.edge_nodes[node_id]
        
    def cleanup_dead_nodes_loop(self):
        while True:
            try:
                self._cleanup_dead_nodes()
                time.sleep(self.cleanup_dead_nodes_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.cleanup_dead_nodes_interval)

    def start_cleanup_dead_nodes_containers(self):
        if self.is_cleaning:
            return
        self.is_cleaning = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_dead_nodes_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        self.logger.info("Cleanup dead nodes thread started")
        
    def stop_cleanup_dead_nodes_containers(self):
        self.is_cleaning = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        self.logger.info("Cleanup dead nodes thread stopped")
        
    def start_all_tasks(self):
        self.start_cleanup_dead_nodes_containers()
        
    def stop_all_tasks(self):
        self.stop_cleanup_dead_nodes_containers()