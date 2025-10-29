#!/usr/bin/env python3
"""
Serverless Edge Computing Simulation - Experiment Runner
Runs comprehensive experiments with different configurations for CVX and Greedy algorithms
"""

import requests
import json
import time
import csv
import os
import subprocess
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment_log.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ExperimentRunner:
    def __init__(self, central_url: str = "http://localhost:8000"):
        self.central_url = central_url
        self.api_base = f"{central_url}/api/v1/central"
        self.results = []
        self.edge_processes = []
        self.current_experiment_id = None
        
    def cleanup_processes(self):
        """Clean up any running edge processes"""
        logger.info("Cleaning up edge processes...")
        for process in self.edge_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self.edge_processes = []
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        logger.info("\nExperiment interrupted. Cleaning up...")
        self.cleanup_processes()
        sys.exit(0)
    
    def wait_for_central_node(self, timeout: int = 60) -> bool:
        """Wait for central node to be ready"""
        logger.info("Waiting for central node to be ready...")
        for _ in range(timeout):
            try:
                response = requests.get(f"{self.api_base}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("Central node is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        logger.error("Central node failed to start within timeout")
        return False
    
    def deploy_edge_nodes(self, num_edges: int, start_port: int = 8001) -> bool:
        """Deploy specified number of edge nodes"""
        logger.info(f"Deploying {num_edges} edge nodes starting from port {start_port}")
        
        try:
            # Kill any existing edge processes first
            self.cleanup_processes()
            
            # Start edge nodes
            for i in range(num_edges):
                node_id = f"edge_{i+1:03d}"
                port = start_port + i
                
                cmd = [
                    "./deploy_edge.sh",
                    "--node-id", node_id,
                    "--central-url", self.central_url,
                    "--port", str(port)
                ]
                
                logger.info(f"Starting {node_id} on port {port}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid
                )
                self.edge_processes.append(process)
                
                # Small delay between node starts
                time.sleep(1)
            
            # Wait for nodes to register
            logger.info("Waiting for edge nodes to register...")
            time.sleep(10)
            
            # Verify nodes are registered
            response = requests.get(f"{self.api_base}/cluster/status")
            if response.status_code == 200:
                cluster_status = response.json()
                registered_edges = len(cluster_status.get('data', {}).get('edge_nodes', []))
                logger.info(f"Successfully registered {registered_edges}/{num_edges} edge nodes")
                return registered_edges >= num_edges * 0.8  # Allow some tolerance
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to deploy edge nodes: {e}")
            return False
    
    def create_users(self, num_users: int) -> bool:
        """Create specified number of user nodes"""
        logger.info(f"Creating {num_users} users...")
        
        try:
            # Clear existing users first
            requests.delete(f"{self.api_base}/delete_all_users")
            time.sleep(2)
            
            created_users = 0
            for i in range(num_users):
                user_data = {
                    "user_id": f"user_{i+1:04d}",
                    "location": {
                        "x": random.randint(0, 1000),
                        "y": random.randint(0, 1000)
                    },
                    "functions": [
                        {
                            "function_name": f"user_function_{i+1}",
                            "image": "python-serverless-handler:latest",
                            "memory_requirement": random.randint(64, 256),
                            "cpu_requirement": random.uniform(0.1, 1.0)
                        }
                    ]
                }
                
                response = requests.post(
                    f"{self.api_base}/create_user_node",
                    json=user_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    created_users += 1
                else:
                    logger.warning(f"Failed to create user {i+1}: {response.text}")
            
            logger.info(f"Successfully created {created_users}/{num_users} users")
            return created_users >= num_users * 0.8  # Allow some tolerance
            
        except Exception as e:
            logger.error(f"Failed to create users: {e}")
            return False
    
    def set_assignment_algorithm(self, algorithm: str) -> bool:
        """Set the assignment algorithm (greedy or convex optimization)"""
        try:
            logger.info(f"Setting assignment algorithm to: {algorithm}")
            response = requests.post(
                f"{self.api_base}/assignment_algorithm",
                json={"algorithm": algorithm},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully set algorithm to {algorithm}")
                return True
            else:
                logger.error(f"Failed to set algorithm: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set assignment algorithm: {e}")
            return False
    
    def run_simulation_workload(self, duration: int = 60) -> Dict[str, Any]:
        """Run simulation workload for specified duration"""
        logger.info(f"Running simulation workload for {duration} seconds...")
        
        # Start simulation
        start_response = requests.post(f"{self.api_base}/start_simulation")
        if start_response.status_code != 200:
            logger.error(f"Failed to start simulation: {start_response.text}")
            return {}
        
        # Let simulation run
        time.sleep(duration)
        
        # Get performance metrics
        metrics_response = requests.get(f"{self.api_base}/performance_metrics")
        metrics = {}
        if metrics_response.status_code == 200:
            metrics = metrics_response.json().get('data', {})
        
        # Stop simulation
        stop_response = requests.post(f"{self.api_base}/stop_simulation")
        if stop_response.status_code != 200:
            logger.warning(f"Failed to stop simulation gracefully: {stop_response.text}")
        
        return metrics
    
    def run_single_experiment(self, num_users: int, num_edges: int, algorithm: str, 
                            experiment_duration: int = 60) -> Dict[str, Any]:
        """Run a single experiment configuration"""
        experiment_start = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {num_users} users, {num_edges} edges, {algorithm} algorithm")
        logger.info(f"{'='*60}")
        
        # Reset simulation state
        requests.post(f"{self.api_base}/reset_simulation")
        time.sleep(2)
        
        # Deploy edge nodes
        if not self.deploy_edge_nodes(num_edges):
            return {"error": "Failed to deploy edge nodes"}
        
        # Create users
        if not self.create_users(num_users):
            return {"error": "Failed to create users"}
        
        # Set algorithm
        if not self.set_assignment_algorithm(algorithm):
            return {"error": f"Failed to set algorithm to {algorithm}"}
        
        # Run workload and collect metrics
        metrics = self.run_simulation_workload(experiment_duration)
        
        experiment_time = time.time() - experiment_start
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "num_users": num_users,
            "num_edges": num_edges,
            "algorithm": algorithm,
            "experiment_duration": experiment_duration,
            "total_experiment_time": experiment_time,
            "metrics": metrics,
            "success": bool(metrics and "error" not in metrics)
        }
        
        logger.info(f"Experiment completed in {experiment_time:.2f} seconds")
        return result
    
    def save_results_to_csv(self, filename: str = None):
        """Save experiment results to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}.csv"
        
        logger.info(f"Saving results to {filename}")
        
        with open(filename, 'w', newline='') as csvfile:
            if not self.results:
                logger.warning("No results to save")
                return
            
            # Get all possible field names
            fieldnames = set()
            for result in self.results:
                fieldnames.update(result.keys())
                if 'metrics' in result and isinstance(result['metrics'], dict):
                    for metric_key in result['metrics'].keys():
                        fieldnames.add(f"metric_{metric_key}")
            
            fieldnames = sorted(list(fieldnames))
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                # Flatten metrics
                row = result.copy()
                if 'metrics' in row and isinstance(row['metrics'], dict):
                    for metric_key, metric_value in row['metrics'].items():
                        row[f"metric_{metric_key}"] = metric_value
                    del row['metrics']
                
                writer.writerow(row)
        
        logger.info(f"Results saved to {filename}")
    
    def run_comprehensive_experiments(self, 
                                    user_ranges: List[int] = None,
                                    edge_ranges: List[int] = None,
                                    algorithms: List[str] = None,
                                    experiment_duration: int = 60,
                                    repetitions: int = 1):
        """Run comprehensive experiments with different configurations"""
        
        # Default ranges
        if user_ranges is None:
            user_ranges = [100, 200, 300, 500, 750, 1000]
        if edge_ranges is None:
            edge_ranges = [10, 20, 30, 50, 75, 100]
        if algorithms is None:
            algorithms = ["greedy", "convex optimization"]
        
        # Setup signal handler for cleanup
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Wait for central node
        if not self.wait_for_central_node():
            logger.error("Central node is not ready. Aborting experiments.")
            return
        
        total_experiments = len(user_ranges) * len(edge_ranges) * len(algorithms) * repetitions
        experiment_count = 0
        
        logger.info(f"Starting comprehensive experiments...")
        logger.info(f"User ranges: {user_ranges}")
        logger.info(f"Edge ranges: {edge_ranges}")
        logger.info(f"Algorithms: {algorithms}")
        logger.info(f"Repetitions: {repetitions}")
        logger.info(f"Total experiments: {total_experiments}")
        
        start_time = time.time()
        
        for rep in range(repetitions):
            for num_users in user_ranges:
                for num_edges in edge_ranges:
                    for algorithm in algorithms:
                        experiment_count += 1
                        
                        logger.info(f"\n[{experiment_count}/{total_experiments}] Rep {rep+1}/{repetitions}")
                        
                        try:
                            result = self.run_single_experiment(
                                num_users, num_edges, algorithm, experiment_duration
                            )
                            result["repetition"] = rep + 1
                            self.results.append(result)
                            
                            # Save intermediate results
                            if experiment_count % 5 == 0:  # Save every 5 experiments
                                self.save_results_to_csv()
                            
                        except Exception as e:
                            logger.error(f"Experiment failed: {e}")
                            self.results.append({
                                "timestamp": datetime.now().isoformat(),
                                "num_users": num_users,
                                "num_edges": num_edges,
                                "algorithm": algorithm,
                                "repetition": rep + 1,
                                "error": str(e),
                                "success": False
                            })
                        
                        # Small break between experiments
                        time.sleep(5)
        
        total_time = time.time() - start_time
        logger.info(f"\nAll experiments completed in {total_time:.2f} seconds")
        
        # Final save
        self.save_results_to_csv()
        
        # Cleanup
        self.cleanup_processes()
        
        # Summary
        successful = sum(1 for r in self.results if r.get('success', False))
        logger.info(f"Experiment Summary: {successful}/{total_experiments} successful")


def main():
    """Main function to run experiments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run serverless edge computing experiments")
    parser.add_argument("--central-url", default="http://localhost:8000", 
                       help="Central node URL (default: http://localhost:8000)")
    parser.add_argument("--user-min", type=int, default=100, 
                       help="Minimum number of users (default: 100)")
    parser.add_argument("--user-max", type=int, default=1000, 
                       help="Maximum number of users (default: 1000)")
    parser.add_argument("--user-step", type=int, default=200, 
                       help="User step size (default: 200)")
    parser.add_argument("--edge-min", type=int, default=10, 
                       help="Minimum number of edges (default: 10)")
    parser.add_argument("--edge-max", type=int, default=100, 
                       help="Maximum number of edges (default: 100)")
    parser.add_argument("--edge-step", type=int, default=20, 
                       help="Edge step size (default: 20)")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Experiment duration in seconds (default: 60)")
    parser.add_argument("--repetitions", type=int, default=1, 
                       help="Number of repetitions per configuration (default: 1)")
    parser.add_argument("--algorithms", nargs="+", 
                       default=["greedy", "convex optimization"],
                       help="Algorithms to test (default: greedy and convex optimization)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test with minimal configurations")
    
    args = parser.parse_args()
    
    # Generate ranges
    if args.quick:
        user_ranges = [100, 500, 1000]
        edge_ranges = [10, 50, 100]
        duration = 30
    else:
        user_ranges = list(range(args.user_min, args.user_max + 1, args.user_step))
        edge_ranges = list(range(args.edge_min, args.edge_max + 1, args.edge_step))
        duration = args.duration
    
    # Create experiment runner
    runner = ExperimentRunner(central_url=args.central_url)
    
    # Run experiments
    runner.run_comprehensive_experiments(
        user_ranges=user_ranges,
        edge_ranges=edge_ranges,
        algorithms=args.algorithms,
        experiment_duration=duration,
        repetitions=args.repetitions
    )
    
    logger.info("Experiment runner completed successfully!")


if __name__ == "__main__":
    main()