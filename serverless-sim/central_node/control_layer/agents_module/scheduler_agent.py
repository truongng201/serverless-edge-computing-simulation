import logging
import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
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
        
        # Thread pool for parallel health checks
        self.max_workers = min(32, 10)  # Max 10 concurrent health checks
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        self.logger.info("Scheduler Agent initialized")
    
    def _check_node_health(self, node_id: str, node) -> tuple:
        """Check health of a single node"""
        for attempt in range(1, self.max_attempts_call + 1):
            try:
                result = requests.get(
                    f"http://{node.endpoint}/api/v1/edge/health",
                    timeout=3  # 3 second timeout per attempt
                )
                if result.status_code == 200:
                    return (node_id, True)
                    
                if attempt < self.max_attempts_call:
                    time.sleep(0.5)  # Brief pause between retries
                    
            except (requests.Timeout, requests.ConnectionError) as e:
                self.logger.debug(f"Node {node_id} health check attempt {attempt}/{self.max_attempts_call} failed: {e}")
                if attempt < self.max_attempts_call:
                    time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Unexpected error checking node {node_id}: {e}")
                break
        
        return (node_id, False)
        
    def _cleanup_dead_nodes(self):
        """Remove nodes that fail health checks"""
        start_time = time.time()
        edge_nodes_snapshot = dict(self.scheduler.edge_nodes)
        
        if not edge_nodes_snapshot:
            return
        
        self.logger.debug(f"Checking health of {len(edge_nodes_snapshot)} edge nodes")
        
        # Submit all health checks to thread pool
        futures = {
            self.executor.submit(self._check_node_health, node_id, node): node_id
            for node_id, node in edge_nodes_snapshot.items()
        }
        
        # Collect results
        dead_nodes: List[str] = []
        for future in as_completed(futures, timeout=10):
            try:
                node_id, is_healthy = future.result(timeout=1)
                if not is_healthy:
                    dead_nodes.append(node_id)
            except Exception as e:
                node_id = futures[future]
                self.logger.error(f"Error checking node {node_id} health: {e}")
                dead_nodes.append(node_id)
        
        # Remove dead nodes
        for node_id in dead_nodes:
            if node_id in self.scheduler.edge_nodes:
                node = self.scheduler.edge_nodes[node_id]
                time_since_heartbeat = time.time() - node.last_heartbeat if node.last_heartbeat else 0
                self.logger.warning(
                    f"Removing dead node: {node_id} "
                    f"(last heartbeat: {time_since_heartbeat:.1f}s ago)"
                )
                del self.scheduler.edge_nodes[node_id]
        
        elapsed_time = time.time() - start_time
        self.logger.info(
            f"Node health check completed: {len(edge_nodes_snapshot) - len(dead_nodes)} alive, "
            f"{len(dead_nodes)} dead in {elapsed_time:.2f}s"
        )
        
    def cleanup_dead_nodes_loop(self):
        """Main cleanup loop"""
        self.logger.info("Cleanup dead nodes loop started")
        
        while self.is_cleaning:
            try:
                loop_start = time.time()
                self._cleanup_dead_nodes()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.cleanup_dead_nodes_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Cleanup took {elapsed:.2f}s, "
                        f"longer than interval {self.cleanup_dead_nodes_interval}s"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                time.sleep(self.cleanup_dead_nodes_interval)
        
        self.logger.info("Cleanup dead nodes loop stopped")

    def start_cleanup_dead_nodes_containers(self):
        """Start cleanup thread"""
        if self.is_cleaning:
            self.logger.warning("Cleanup is already running")
            return
            
        self.is_cleaning = True
        self.cleanup_dead_nodes_thread = threading.Thread(
            target=self.cleanup_dead_nodes_loop,
            name="SchedulerAgent-CleanupDeadNodes"
        )
        self.cleanup_dead_nodes_thread.daemon = True
        self.cleanup_dead_nodes_thread.start()
        
        self.logger.info("Cleanup dead nodes thread started")
        
    def stop_cleanup_dead_nodes_containers(self):
        """Stop cleanup thread"""
        self.logger.info("Stopping cleanup dead nodes thread...")
        self.is_cleaning = False
        
        if self.cleanup_dead_nodes_thread and self.cleanup_dead_nodes_thread.is_alive():
            self.cleanup_dead_nodes_thread.join(timeout=5)
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True, cancel_futures=True)
        
        self.logger.info("Cleanup dead nodes thread stopped")
        
    def start_all_tasks(self):
        """Start all background tasks"""
        self.start_cleanup_dead_nodes_containers()
        
    def stop_all_tasks(self):
        """Stop all background tasks"""
        self.stop_cleanup_dead_nodes_containers()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.stop_all_tasks()
        except:
            pass