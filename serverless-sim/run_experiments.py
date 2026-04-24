import requests
import time
import csv
import os
import subprocess
import signal
import sys
from datetime import datetime
from typing import Dict, Any
from collections import OrderedDict, defaultdict
import matplotlib.pyplot as plt
import math



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
                response = requests.get(f"{self.api_base}/health", timeout=600)
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
            # Set expected total edge nodes for proper grid placement
            os.environ["EXPECTED_EDGE_NODES"] = str(num_edges)
            
            self.cleanup_processes()
            
            # Start edge nodes
            for i in range(num_edges):
                node_id = f"edge_{i+1:03d}"
                port = start_port + i
                
                cmd = [
                    "./deploy_edge.sh",
                    "--node-id", node_id,
                    "--central-url", self.central_url,
                    "--port", str(port),
                    "--cpus", "2",
                    "--memory", "1g"
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
                timeout=600
            )
            
            if response.status_code == 200:
                print(f"Successfully set algorithm to {algorithm}")
                response = requests.get(f"{self.api_base}/assignment_algorithm", timeout=600)
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
        # Use taxiD_Replay for proper predictive model testing (trained on T-drive data)
        dataset_name = 'taxiD_Replay'
        try:
            print(f"Setting dataset '{dataset_name}' with num_users={num_users}")
            payload = {"dataset_name": dataset_name, "sample_size": num_users}
            response = requests.post(f"{self.api_base}/set_dataset", json=payload, timeout=600)
            if response.status_code == 200:
                return True
            else:
                print(f"Failed to set dataset: {response.status_code} {response.text}")
                return False
        except Exception as e:
            print(f"Failed to set dataset: {e}")
            return False
    
    def run_simulation_workload(self, duration: int = 50, delay_time: int = 1) -> Dict[str, Any]:
        print(f"Running simulation workload for {duration} seconds...")
        
        # Start simulation
        start_response = requests.post(f"{self.api_base}/start_simulation")
        if start_response.status_code != 200:
            print(f"Failed to start simulation: {start_response.text}")
            return {}
        else:
            print("Simulation started successfully")
        metrics = {}
        for timestep in range(duration // delay_time):
            res = requests.get(f"{self.api_base}/get_all_users")
            if res.status_code != 200:
                print(f"Failed to update users at timestep {timestep + 1}")
                continue
            metrics_response = requests.get(f"{self.api_base}/performance_metrics")
            if metrics_response.status_code == 200:
                m = metrics_response.json().get('data', {}) or {}
                # Keep total turnaround time for plotting, but also store warm/cold totals for analysis.
                # Also include energy consumption metrics
                metrics[timestep + 1] = {
                    "total_turnaround_time": float(m.get("total_turnaround_time", 0.0) or 0.0),
                    "total_turnaround_time_warm": float(m.get("total_turnaround_time_warm", 0.0) or 0.0),
                    "total_turnaround_time_cold": float(m.get("total_turnaround_time_cold", 0.0) or 0.0),
                    "total_turnaround_time_unknown": float(m.get("total_turnaround_time_unknown", 0.0) or 0.0),
                    "warm_count": int(float(m.get("warm_count", 0) or 0)),
                    "cold_count": int(float(m.get("cold_count", 0) or 0)),
                    "unknown_count": int(float(m.get("unknown_count", 0) or 0)),
                    # Energy consumption metrics
                    "static_energy_j": float(m.get("static_energy_j", 0.0) or 0.0),
                    "dynamic_energy_j": float(m.get("dynamic_energy_j", 0.0) or 0.0),
                    "network_energy_j": float(m.get("network_energy_j", 0.0) or 0.0),
                    "cold_start_energy_j": float(m.get("cold_start_energy_j", 0.0) or 0.0),
                    "total_energy_j": float(m.get("total_energy_j", 0.0) or 0.0),
                    "total_energy_wh": float(m.get("total_energy_wh", 0.0) or 0.0),
                    "average_power_w": float(m.get("average_power_w", 0.0) or 0.0),
                }
                print(
                    f"Timestep {timestep + 1}: "
                    f"Total={metrics[timestep + 1]['total_turnaround_time']:.1f} | "
                    f"Warm={metrics[timestep + 1]['total_turnaround_time_warm']:.1f} "
                    f"(n={metrics[timestep + 1]['warm_count']}) | "
                    f"Cold={metrics[timestep + 1]['total_turnaround_time_cold']:.1f} "
                    f"(n={metrics[timestep + 1]['cold_count']}) | "
                    f"Energy={metrics[timestep + 1]['total_energy_j']:.2f}J "
                    f"(Power={metrics[timestep + 1]['average_power_w']:.1f}W)"
                )
            else:
                print(f"Failed to get metrics at timestep {timestep + 1}: {metrics_response.text}")
            time.sleep(delay_time)

        # Stop simulation
        stop_response = requests.post(f"{self.api_base}/stop_simulation")
        if stop_response.status_code != 200:
            print(f"Failed to stop simulation gracefully: {stop_response.text}")
        
        return metrics
    
    def run_single_experiment(self, num_users: int, num_edges: int, algorithm: str, 
                            experiment_duration: int = 600) -> Dict[str, Any]:
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
            return {"error": f"Failed to set dataset taxiD_Replay for {num_users} users"}
        
        metrics = self.run_simulation_workload(duration=experiment_duration)
        
        experiment_time = time.time() - experiment_start
        
        # Calculate total energy consumption across all timesteps
        total_energy_j = 0.0
        total_cold_start_energy_j = 0.0
        total_network_energy_j = 0.0
        if metrics:
            for ts_metrics in metrics.values():
                total_energy_j += ts_metrics.get("total_energy_j", 0.0)
                total_cold_start_energy_j += ts_metrics.get("cold_start_energy_j", 0.0)
                total_network_energy_j += ts_metrics.get("network_energy_j", 0.0)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "num_users": num_users,
            "num_edges": num_edges,
            "algorithm": algorithm,
            "experiment_duration": experiment_duration,
            "total_experiment_time": experiment_time,
            "metrics": metrics,
            "total_energy_j": total_energy_j,
            "total_cold_start_energy_j": total_cold_start_energy_j,
            "total_network_energy_j": total_network_energy_j,
            "success": True if metrics and len(metrics) > 0 else False
        }
        
        print(f"Experiment completed in {experiment_time:.2f} seconds")
        print(f"  Total Energy: {total_energy_j:.2f}J ({total_energy_j/3600:.4f}Wh)")
        print(f"  Cold Start Energy: {total_cold_start_energy_j:.2f}J")
        print(f"  Network Energy: {total_network_energy_j:.2f}J")
        return result
    
    def save_results_to_csv(self, filename: str = None):
        """Save experiment results to CSV with one row per metric timestep.

        Output columns:
          timestamp, num_users, num_edges, algorithm, experiment_duration,
          total_experiment_time, timestep, metric, success
        """
        import json

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}.csv"

        print(f"Saving results to {filename}")
        if not self.results:
            print("No results to save")
            return

        fieldnames = [
            "num_users",
            "num_edges",
            "algorithm",
            "experiment_duration",
            "total_experiment_time",
            "timestep",
            "total_turnaround_time",
            "total_turnaround_time_warm",
            "total_turnaround_time_cold",
            "total_turnaround_time_unknown",
            "warm_count",
            "cold_count",
            "unknown_count",
            # Energy consumption metrics
            "static_energy_j",
            "dynamic_energy_j",
            "network_energy_j",
            "cold_start_energy_j",
            "total_energy_j",
            "total_energy_wh",
            "average_power_w",
        ]

        try:
            with open(filename, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for result in self.results:
                    base_row = {
                        "num_users": result.get("num_users", ""),
                        "num_edges": result.get("num_edges", ""),
                        "algorithm": result.get("algorithm", ""),
                        "experiment_duration": result.get("experiment_duration", ""),
                        "total_experiment_time": result.get("total_experiment_time", ""),
                    }

                    metrics = result.get("metrics")
                    # If metrics is a dict with per-timestep values, write one row per timestep
                    if isinstance(metrics, dict) and metrics:
                        # Sort keys numerically when possible
                        def key_to_int(k):
                            try:
                                return int(k)
                            except Exception:
                                return k
                        for k, v in sorted(metrics.items(), key=lambda kv: key_to_int(kv[0])):
                            try:
                                timestep = int(k)
                            except Exception:
                                timestep = k
                            row = dict(base_row)
                            row["timestep"] = timestep
                            if isinstance(v, dict):
                                row["total_turnaround_time"] = v.get("total_turnaround_time", "")
                                row["total_turnaround_time_warm"] = v.get("total_turnaround_time_warm", "")
                                row["total_turnaround_time_cold"] = v.get("total_turnaround_time_cold", "")
                                row["total_turnaround_time_unknown"] = v.get("total_turnaround_time_unknown", "")
                                row["warm_count"] = v.get("warm_count", "")
                                row["cold_count"] = v.get("cold_count", "")
                                row["unknown_count"] = v.get("unknown_count", "")
                                # Energy consumption metrics
                                row["static_energy_j"] = v.get("static_energy_j", "")
                                row["dynamic_energy_j"] = v.get("dynamic_energy_j", "")
                                row["network_energy_j"] = v.get("network_energy_j", "")
                                row["cold_start_energy_j"] = v.get("cold_start_energy_j", "")
                                row["total_energy_j"] = v.get("total_energy_j", "")
                                row["total_energy_wh"] = v.get("total_energy_wh", "")
                                row["average_power_w"] = v.get("average_power_w", "")
                            else:
                                # Backward-compatible: older runs stored just a float total_turnaround_time
                                row["total_turnaround_time"] = v
                            writer.writerow(row)
                    else:
                        row = dict(base_row)
                        row["timestep"] = ""
                        try:
                            row["total_turnaround_time"] = json.dumps(metrics) if metrics is not None else ""
                        except Exception:
                            row["total_turnaround_time"] = str(metrics)
                        writer.writerow(row)

            print(f"Results saved to {filename}")
        except Exception as e:
            print(f"Failed to save results to CSV: {e}")
        return filename
    
    def load_results_from_csv(self, filename: str):
        """Load the CSV produced by save_results_to_csv into structured dict:
        data[(num_users,num_edges)][algorithm] = OrderedDict[timestep] = value
        """
        data = defaultdict(lambda: defaultdict(OrderedDict))
        try:
            with open(filename, newline='') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    try:
                        num_users = int(r.get("num_users") or 0)
                        num_edges = int(r.get("num_edges") or 0)
                        alg = r.get("algorithm", "").strip()
                        t = r.get("timestep", "")
                        if t == "":
                            continue
                        timestep = int(t)
                        val = r.get("total_turnaround_time", "")
                        if val == "":
                            continue
                        value = float(val)
                    except Exception:
                        continue
                    combo = (num_users, num_edges)
                    data[combo][alg][timestep] = value
        except Exception as e:
            print(f"Failed to load CSV {filename}: {e}")
            return {}
        # ensure ordered timesteps
        for combo in list(data.keys()):
            for alg in list(data[combo].keys()):
                data[combo][alg] = OrderedDict(sorted(data[combo][alg].items(), key=lambda kv: kv[0]))
        return data
    
    def load_energy_results_from_csv(self, filename: str):
        """Load energy consumption data from CSV.
        
        Returns:
            data[(num_users,num_edges)][algorithm] = OrderedDict[timestep] = {energy_metrics}
        """
        data = defaultdict(lambda: defaultdict(OrderedDict))
        try:
            with open(filename, newline='') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    try:
                        num_users = int(r.get("num_users") or 0)
                        num_edges = int(r.get("num_edges") or 0)
                        alg = r.get("algorithm", "").strip()
                        t = r.get("timestep", "")
                        if t == "":
                            continue
                        timestep = int(t)
                        
                        # Extract energy metrics
                        energy_metrics = {
                            "static_energy_j": float(r.get("static_energy_j", 0) or 0),
                            "dynamic_energy_j": float(r.get("dynamic_energy_j", 0) or 0),
                            "network_energy_j": float(r.get("network_energy_j", 0) or 0),
                            "cold_start_energy_j": float(r.get("cold_start_energy_j", 0) or 0),
                            "total_energy_j": float(r.get("total_energy_j", 0) or 0),
                            "total_energy_wh": float(r.get("total_energy_wh", 0) or 0),
                            "average_power_w": float(r.get("average_power_w", 0) or 0),
                        }
                    except Exception:
                        continue
                    combo = (num_users, num_edges)
                    data[combo][alg][timestep] = energy_metrics
        except Exception as e:
            print(f"Failed to load energy data from CSV {filename}: {e}")
            return {}
        
        # ensure ordered timesteps
        for combo in list(data.keys()):
            for alg in list(data[combo].keys()):
                data[combo][alg] = OrderedDict(sorted(data[combo][alg].items(), key=lambda kv: kv[0]))
        return data
    
    def run_comprehensive_experiments(self, user_ranges = [], edge_ranges = [], algorithms = [], experiment_duration = 100):
        if not user_ranges:
            user_ranges = [500]  # 100 users
        if not edge_ranges:
            edge_ranges = [200]
        if not algorithms:
            algorithms = ["predictive", "round_robin", "random", "greedy"]
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        if not self.wait_for_central_node():
            print("Central node is not ready. Aborting experiments.")
            return
        
        total_experiments = len(user_ranges) * len(edge_ranges) * len(algorithms)
        
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
                    try:
                        result = self.run_single_experiment(
                            num_users, num_edges, algorithm, experiment_duration
                        )
                        self.results.append(result)
                        
                        
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
        self.save_results_to_csv()
        print(f"\nAll experiments completed in {total_time:.2f} seconds")
        successful = sum(1 for r in self.results if r.get('success', False))
        print(f"Experiment Summary: {successful}/{total_experiments} successful")


def main():
    central_url = "http://localhost:8000"
    runner = ExperimentRunner(central_url=central_url)
    
    runner.run_comprehensive_experiments()
    print("Experiment runner completed successfully!")


if __name__ == "__main__":
    main()
