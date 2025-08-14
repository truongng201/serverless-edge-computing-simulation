import logging
import threading
import time

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
        
        self.logger.info("Scheduler Agent initialized")
        
    def _cleanup_dead_nodes(self):    
        current_time = time.time()
        dead_nodes = []
        
        for node_id, node in self.scheduler.edge_nodes.items():
            if current_time - node.last_heartbeat > Config.EDGE_NODE_HEARTBEAT_TIMEOUT:
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