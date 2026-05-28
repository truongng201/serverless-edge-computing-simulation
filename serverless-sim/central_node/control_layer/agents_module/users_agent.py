import logging
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, Any, List
from collections import defaultdict
from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.models import UserNodeInfo

from config import Config

class UsersAgent:
    def __init__(self, scheduler: Scheduler):
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler

        # Thread pool for parallel execution
        self.max_workers = 100
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # HTTP Session with connection pooling
        self.session = requests.Session()
        retry_strategy = Retry(
            total=1,  # Reduced retries
            backoff_factor=0.05,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1000,
            pool_maxsize=100
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Execute functions
        self.execute_function_thread = None
        self.is_executing = False

        # Node health tracking
        self.node_failures = defaultdict(int)
        self.node_last_success = {}
        self.max_failures_before_skip = 5

        # Batch configuration
        self.batch_size = 25  # Process users in batches of 25

        self.logger.info(f"Users Agent initialized with {self.max_workers} worker threads, batch size {self.batch_size}")

    def _is_node_healthy(self, node_id: str) -> bool:
        """Check if a node should be tried based on recent failures"""
        if node_id not in self.node_failures:
            return True
        
        failures = self.node_failures[node_id]
        if failures >= self.max_failures_before_skip:
            # Check if enough time has passed to retry
            last_success = self.node_last_success.get(node_id, 0)
            if time.time() - last_success > 60:  # Retry after 1 minute
                self.logger.info(f"Retrying previously failed node: {node_id}")
                self.node_failures[node_id] = 0
                return True
            return False
        return True

    def _mark_node_success(self, node_id: str):
        """Mark a node as successful"""
        self.node_failures[node_id] = 0
        self.node_last_success[node_id] = time.time()

    def _mark_node_failure(self, node_id: str):
        """Mark a node as failed"""
        self.node_failures[node_id] += 1
        if self.node_failures[node_id] == self.max_failures_before_skip:
            self.logger.warning(f"Node {node_id} marked as unhealthy after {self.max_failures_before_skip} failures")

    def _execute_single_function(self, user_node: UserNodeInfo) -> Dict[str, Any]:
        """Execute function for a single user node"""
        try:
            assigned_node = user_node.assigned_node_id
            
            if not assigned_node:
                return {"user_id": user_node.user_id, "status": "skipped", "reason": "no_assigned_node"}
            
            # Check node health
            if not self._is_node_healthy(assigned_node):
                return {"user_id": user_node.user_id, "status": "skipped", "reason": "node_unhealthy", "node": assigned_node}
            
            # Access central_node directly from scheduler
            central_node = self.scheduler.central_node
            
            # Execute on central node
            if assigned_node == central_node['node_id']:
                try:
                    url = f"http://{central_node['endpoint']}/api/v1/central/execute"
                    
                    result = self.session.post(
                        url,
                        json={"user_id": user_node.user_id},
                        timeout=10  # Increased to 10 seconds
                    )
                    
                    if result.status_code == 200:
                        data = result.json().get("data", {})
                        user_node.latency.computation_delay = data.get("execution_time", 0.0) * 1000
                        user_node.latency.container_status = data.get("container_status", "unknown")
                        user_node.last_executed = time.time()
                        self._mark_node_success(assigned_node)
                        
                        return {
                            "user_id": user_node.user_id,
                            "status": "success",
                            "node": "central"
                        }
                    else:
                        self._mark_node_failure(assigned_node)
                        return {"user_id": user_node.user_id, "status": "failed", "node": "central"}
                        
                except requests.Timeout:
                    self._mark_node_failure(assigned_node)
                    return {"user_id": user_node.user_id, "status": "timeout", "node": "central"}
                except requests.RequestException:
                    self._mark_node_failure(assigned_node)
                    return {"user_id": user_node.user_id, "status": "error", "node": "central"}
            
            # Execute on edge node
            edge_node = self.scheduler.edge_nodes.get(assigned_node)
            if edge_node:
                try:
                    url = f"http://{edge_node.endpoint}/api/v1/edge/execute"
                    
                    result = self.session.post(
                        url,
                        json={"user_id": user_node.user_id},
                        timeout=10  # Increased to 10 seconds
                    )
                    
                    if result.status_code == 200:
                        data = result.json()
                        user_node.latency.computation_delay = data.get("execution_time", 0.0) * 1000
                        user_node.latency.container_status = data.get("container_status", "unknown")
                        user_node.last_executed = time.time()
                        self._mark_node_success(assigned_node)
                        
                        return {
                            "user_id": user_node.user_id,
                            "status": "success",
                            "node": assigned_node
                        }
                    else:
                        self._mark_node_failure(assigned_node)
                        return {"user_id": user_node.user_id, "status": "failed", "node": assigned_node}
                        
                except requests.Timeout:
                    self._mark_node_failure(assigned_node)
                    return {"user_id": user_node.user_id, "status": "timeout", "node": assigned_node}
                except requests.RequestException:
                    self._mark_node_failure(assigned_node)
                    return {"user_id": user_node.user_id, "status": "error", "node": assigned_node}
            else:
                return {"user_id": user_node.user_id, "status": "error", "reason": "edge_node_not_found"}
                
        except Exception as e:
            self.logger.error(f"Unexpected error for user {user_node.user_id}: {e}")
            return {"user_id": user_node.user_id, "status": "error", "error": str(e)}

    def _execute_batch(self, user_batch: List[UserNodeInfo]) -> Dict[str, int]:
        """Execute a batch of users"""
        futures = {
            self.executor.submit(self._execute_single_function, user_node): user_node
            for user_node in user_batch
        }
        
        stats = {
            "success": 0,
            "failed": 0,
            "timeout": 0,
            "skipped": 0,
            "error": 0,
            "completed": 0
        }
        
        try:
            for future in as_completed(futures, timeout=10):  # 10 seconds per batch
                stats["completed"] += 1
                try:
                    result = future.result(timeout=1)
                    status = result.get("status", "error")
                    stats[status] = stats.get(status, 0) + 1
                except Exception:
                    stats["error"] += 1
                    
        except TimeoutError:
            unfinished = len(futures) - stats["completed"]
            if unfinished > 0:
                self.logger.warning(f"Batch timeout: {stats['completed']}/{len(futures)} completed")
            for future in futures:
                if not future.done():
                    future.cancel()
        
        return stats

    def _execute_function(self):
        """Execute functions for all user nodes in batches"""
        start_time = time.time()
        
        user_nodes_snapshot = list(self.scheduler.user_nodes.values())
        
        if not user_nodes_snapshot:
            return
        
        total_users = len(user_nodes_snapshot)
        self.logger.info(f"Executing functions for {total_users} users in batches of {self.batch_size}")
        
        # Split into batches
        batches = [
            user_nodes_snapshot[i:i + self.batch_size]
            for i in range(0, total_users, self.batch_size)
        ]
        
        # Execute batches
        total_stats = defaultdict(int)
        for batch_num, batch in enumerate(batches, 1):
            batch_start = time.time()
            stats = self._execute_batch(batch)
            
            # Aggregate stats
            for key, value in stats.items():
                total_stats[key] += value
            
            batch_elapsed = time.time() - batch_start
            self.logger.debug(
                f"Batch {batch_num}/{len(batches)}: {stats['success']} succeeded, "
                f"{stats['timeout']} timed out in {batch_elapsed:.2f}s"
            )
            
            # Small delay between batches to avoid overwhelming nodes
            if batch_num < len(batches):
                time.sleep(0.2)
        
        elapsed_time = time.time() - start_time
        
        self.logger.info(
            f"Execution complete: {total_stats['success']} succeeded, "
            f"{total_stats['failed']} failed, {total_stats['timeout']} timed out, "
            f"{total_stats['skipped']} skipped, {total_stats['error']} errors "
            f"({total_stats['completed']}/{total_users} total) in {elapsed_time:.2f}s"
        )

    def execute_function_loop(self):
        """Main loop for executing functions periodically"""
        self.logger.info("✅ Function execution loop started")
        
        iteration = 0
        while self.is_executing:
            iteration += 1
            
            try:
                loop_start = time.time()
                
                user_count = len(self.scheduler.user_nodes)
                if user_count == 0:
                    if iteration % 10 == 1:
                        self.logger.info(f"Iteration {iteration} - waiting for users...")
                else:
                    if iteration == 1 or iteration % 5 == 0:
                        self.logger.info(f"Iteration {iteration} - {user_count} users active")
                
                self._execute_function()
                
                # Calculate sleep time
                elapsed = time.time() - loop_start
                sleep_time = max(0, Config.DEFAULT_EXECUTION_TIME_INTERVAL - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"Execution took {elapsed:.2f}s, "
                        f"longer than interval {Config.DEFAULT_EXECUTION_TIME_INTERVAL}s"
                    )
                    time.sleep(1)  # Minimum sleep
                    
            except Exception as e:
                self.logger.error(f"Error in loop iteration {iteration}: {e}", exc_info=True)
                time.sleep(Config.DEFAULT_EXECUTION_TIME_INTERVAL)
        
        self.logger.info(f"🛑 Function execution loop stopped after {iteration} iterations")

    def start_execute_function_containers(self):
        """Start the function execution thread"""
        if self.is_executing:
            self.logger.warning("Function execution is already running")
            return
        
        self.logger.info("Starting function execution thread...")
        self.is_executing = True
        
        self.execute_function_thread = threading.Thread(
            target=self.execute_function_loop,
            name="UsersAgent-ExecuteFunction"
        )
        self.execute_function_thread.daemon = True
        self.execute_function_thread.start()
        
        time.sleep(0.5)
        if self.execute_function_thread.is_alive():
            self.logger.info("✅ Function execution thread started successfully")
        else:
            self.logger.error("❌ Function execution thread failed to start!")
        
    def stop_execute_function_containers(self):
        """Stop the function execution thread"""
        self.logger.info("Stopping function execution thread...")
        self.is_executing = False
        
        if self.execute_function_thread and self.execute_function_thread.is_alive():
            self.execute_function_thread.join(timeout=10)
        
        self.session.close()
        self.executor.shutdown(wait=True, cancel_futures=True)
        
        self.logger.info("Function execution thread stopped")

    def start_all_tasks(self):
        """Start all background tasks"""
        self.logger.info("Starting all UsersAgent tasks...")
        self.start_execute_function_containers()
        self.logger.info("All UsersAgent tasks started")
        
    def stop_all_tasks(self):
        """Stop all background tasks"""
        self.stop_execute_function_containers()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.stop_all_tasks()
        except:
            pass