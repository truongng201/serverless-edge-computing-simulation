import requests
import time
import csv
import os
import subprocess
import signal
import sys
from datetime import datetime
from typing import Dict, Any



class ExperimentRunner:
    def __init__(self, central_url: str = "http://localhost:8000"):
        self.central_url = central_url
        self.api_base = f"{central_url}/api/v1/central"
        self.results = []
        self.edge_processes = []
        self.current_experiment_id = None
        
    def cleanup_processes(self):
        print("Cleaning up edge processes...")
        for process in self.edge_processes:
            try:
                # Try to terminate the whole process group so any children started by the shell are killed
                try:
                    pgid = os.getpgid(process.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except Exception as e:
                    print(f"Failed to killpg: {e}. Falling back to terminate() on pid {process.pid}")
                    process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    # If still alive, force kill the process group
                    pgid = os.getpgid(process.pid)
                    print(f"Force killing process group {pgid} (pid {process.pid}) with SIGKILL")
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    print(f"Force killing pid {process.pid}")
                    process.kill()
        self.edge_processes = []
    
    def signal_handler(self):
        print("\nExperiment interrupted. Cleaning up...")
        self.cleanup_processes()
        sys.exit(0)
    
    def wait_for_central_node(self, timeout: int = 60) -> bool:
        print("Waiting for central node to be ready...")
        for _ in range(timeout):
            try:
                response = requests.get(f"{self.api_base}/health", timeout=5)
                if response.status_code == 200:
                    print("Central node is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        print("Central node failed to start within timeout")
        return False
    
    def deploy_edge_nodes(self, num_edges: int, start_port: int = 5001) -> bool:
        print(f"\n{'-'*40}")
        print(f"Deploying {num_edges} edge nodes starting from port {start_port}")
        print(f"{'-'*40}")
        try:
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
                
                print(f"Starting {node_id} on port {port}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True  # create a new session so we can kill the entire group with os.killpg
                )
                self.edge_processes.append(process)
            
            print("Waiting for edge nodes to register...")
            time.sleep(num_edges * 2 // 10)  # Wait time proportional to number of edges
            
            response = requests.get(f"{self.api_base}/cluster/status")
            if response.status_code == 200:
                cluster_status = response.json()
                registered_edges = len(cluster_status.get('data', {}).get('cluster_info', {}).get('edge_nodes_info', []))
                print(f"Successfully registered {registered_edges}/{num_edges} edge nodes")
                return registered_edges >= num_edges * 0.8  # Allow some tolerance
            
            return False
            
        except Exception as e:
            print(f"Failed to deploy edge nodes: {e}")
            return False
    
    def set_assignment_algorithm(self, algorithm: str) -> bool:
        try:
            print(f"Setting assignment algorithm to: {algorithm}")
            response = requests.post(
                f"{self.api_base}/assignment_algorithm",
                json={"algorithm": algorithm},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"Successfully set algorithm to {algorithm}")
                response = requests.get(f"{self.api_base}/assignment_algorithm", timeout=10)
                if response.status_code == 200:
                    current_algorithm = response.json().get('data', {}).get('algorithm', '')
                    if current_algorithm == algorithm:
                        return True
                    else:
                        print(f"Algorithm mismatch: expected {algorithm}, got {current_algorithm}")
                        return False
            else:
                print(f"Failed to set algorithm: {response.text}")
                return False
                
        except Exception as e:
            print(f"Failed to set assignment algorithm: {e}")
            return False

    def set_dataset(self, num_users: int) -> bool:
        dataset_name = 'random_generated'
        try:
            print(f"Setting dataset '{dataset_name}' with num_users={num_users}")
            payload = {"dataset_name": dataset_name, "sample_size": int(num_users)}
            response = requests.post(f"{self.api_base}/set_dataset", json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"Failed to set dataset: {response.status_code} {response.text}")
                return False
        except Exception as e:
            print(f"Failed to set dataset: {e}")
            return False
    
    def run_simulation_workload(self, duration: int = 60) -> Dict[str, Any]:
        """Run simulation workload for specified duration"""
        print(f"Running simulation workload for {duration} seconds...")
        
        # Start simulation
        start_response = requests.post(f"{self.api_base}/start_simulation")
        if start_response.status_code != 200:
            print(f"Failed to start simulation: {start_response.text}")
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
            print(f"Failed to stop simulation gracefully: {stop_response.text}")
        
        return metrics
    
    def run_single_experiment(self, num_users: int, num_edges: int, algorithm: str, 
                            experiment_duration: int = 60) -> Dict[str, Any]:
        """Run a single experiment configuration"""
        experiment_start = time.time()
        print(f"\n{'='*60}")
        print(f"EXPERIMENT: {num_users} users, {num_edges} edges, {algorithm} algorithm")
        print(f"{'='*60}")
        
        res = requests.post(f"{self.api_base}/reset_simulation")
        
        if res.status_code != 200:
            return {"error": "Failed to reset simulation"}
        else:
            print("Simulation reset successfully")
        time.sleep(2)
        
        # Set algorithm
        if not self.set_assignment_algorithm(algorithm):
            return {"error": f"Failed to set algorithm to {algorithm}"}
        
        if not self.set_dataset(num_users):
            return {"error": f"Failed to set dataset random_generated for {num_users} users"}
        
        experiment_time = time.time() - experiment_start
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "num_users": num_users,
            "num_edges": num_edges,
            "algorithm": algorithm,
            "experiment_duration": experiment_duration,
            "total_experiment_time": experiment_time,
            # "metrics": metrics,
            # "success": bool(metrics and "error" not in metrics)
        }
        
        print(f"Experiment completed in {experiment_time:.2f} seconds")
        return result
    
    def save_results_to_csv(self, filename: str = None):
        """Save experiment results to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}.csv"
        
        print(f"Saving results to {filename}")
        
        with open(filename, 'w', newline='') as csvfile:
            if not self.results:
                print("No results to save")
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
        
        print(f"Results saved to {filename}")
    
    def run_comprehensive_experiments(self, user_ranges = [], edge_ranges = [], algorithms = [], experiment_duration = 600):
        if not user_ranges:
            user_ranges = [100, 200, 300, 400, 500]
        if not edge_ranges:
            edge_ranges = [40, 50]
        if not algorithms:
            algorithms = ["greedy", "convex optimization"]
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        if not self.wait_for_central_node():
            print("Central node is not ready. Aborting experiments.")
            return
        
        total_experiments = len(user_ranges) * len(edge_ranges) * len(algorithms)
        experiment_count = 0
        
        print(f"Starting comprehensive experiments...")
        print(f"User ranges: {user_ranges}")
        print(f"Edge ranges: {edge_ranges}")
        print(f"Algorithms: {algorithms}")
        print(f"Total experiments: {total_experiments}")
        
        start_time = time.time()
        for num_edges in edge_ranges:
            if not self.deploy_edge_nodes(num_edges):
                print(f"Failed to deploy {num_edges} edge nodes. Skipping this configuration.")
                continue
            for num_users in user_ranges:
                for algorithm in algorithms:
                    experiment_count += 1
                    
                    try:
                        result = self.run_single_experiment(
                            num_users, num_edges, algorithm, experiment_duration
                        )
                        # self.results.append(result)
                        # if experiment_count % 5 == 0:  # Save every 5 experiments
                        #     self.save_results_to_csv()
                        
                    except Exception as e:
                        print(f"Experiment failed: {e}")
                        self.results.append({
                            "timestamp": datetime.now().isoformat(),
                            "num_users": num_users,
                            "num_edges": num_edges,
                            "algorithm": algorithm,
                            "error": str(e),
                            "success": False
                        })
                    
                    time.sleep(5)
            res = requests.post(f"{self.api_base}/reset_simulation")
        
            if res.status_code != 200:
                return {"error": "Failed to reset simulation"}
            else:
                print("Simulation reset successfully")
            self.cleanup_processes()
        
        total_time = time.time() - start_time
        print(f"\nAll experiments completed in {total_time:.2f} seconds")
        # self.save_results_to_csv()
        successful = sum(1 for r in self.results if r.get('success', False))
        print(f"Experiment Summary: {successful}/{total_experiments} successful")


def main():
    central_url = "http://localhost:8000"
    runner = ExperimentRunner(central_url=central_url)
    
    runner.run_comprehensive_experiments()
    print("Experiment runner completed successfully!")


if __name__ == "__main__":
    main()