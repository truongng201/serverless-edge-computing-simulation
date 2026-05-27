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
        self.current_csv_filename = None

    @staticmethod
    def _csv_fieldnames():
        return [
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
        ]

    def init_results_csv(self, filename: str = None) -> str:
        """Create the CSV upfront so each finished experiment can append immediately."""
        if filename:
            self.current_csv_filename = filename
        elif not self.current_csv_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_csv_filename = f"experiment_results_{timestamp}.csv"

        fieldnames = self._csv_fieldnames()
        if not os.path.exists(self.current_csv_filename) or os.path.getsize(self.current_csv_filename) == 0:
            with open(self.current_csv_filename, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        return self.current_csv_filename

    def append_result_to_csv(self, result: Dict[str, Any], filename: str = None) -> str:
        """Append a single experiment result to CSV immediately."""
        import json

        csv_filename = self.init_results_csv(filename)
        fieldnames = self._csv_fieldnames()

        base_row = {
            "num_users": result.get("num_users", ""),
            "num_edges": result.get("num_edges", ""),
            "algorithm": result.get("algorithm", ""),
            "experiment_duration": result.get("experiment_duration", ""),
            "total_experiment_time": result.get("total_experiment_time", ""),
        }

        with open(csv_filename, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            metrics = result.get("metrics")
            if isinstance(metrics, dict) and metrics:
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
                    else:
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
            csvfile.flush()
        return csv_filename
        
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
        """Register `num_edges` virtual edges with the central node.

        In simulated mode (Config.EXECUTION_MODE='simulated') the central does not
        call back into the edge processes — they are needed only as registered
        endpoints for the scheduler's grid placement and metrics bookkeeping.
        We therefore register them directly via /nodes/register instead of
        spawning real Flask processes (which also avoids the bash-only
        deploy_edge.sh on Windows).

        Set env SPAWN_REAL_EDGES=1 to fall back to the legacy spawn path
        (only useful for EXECUTION_MODE='real' on Linux/macOS).
        """
        print(f"\n{'-'*40}")
        print(f"Deploying {num_edges} edge nodes starting from port {start_port}")
        print(f"{'-'*40}")
        os.environ["EXPECTED_EDGE_NODES"] = str(num_edges)

        spawn_real = os.getenv("SPAWN_REAL_EDGES", "0").lower() in ("1", "true", "yes")
        if spawn_real:
            return self._spawn_real_edges(num_edges, start_port)

        # Fast path: register virtual edges directly.
        try:
            self.cleanup_processes()
            # Clear any edges left over from a previous EDGE_RANGES iteration so
            # the new fleet size is exactly num_edges (not max(prev, num_edges)).
            try:
                clear_resp = requests.delete(f"{self.api_base}/nodes", timeout=10)
                if clear_resp.status_code == 200:
                    body = clear_resp.json() if clear_resp.content else {}
                    cleared = (body.get("data") or {}).get("cleared", 0)
                    if cleared:
                        print(f"Cleared {cleared} stale edge node(s) before deploy")
                else:
                    print(f"WARN: clear-edges returned {clear_resp.status_code} (ok if endpoint missing on older central)")
            except Exception as e:
                print(f"WARN: failed to clear stale edges: {e}")
            registered = 0
            for i in range(num_edges):
                node_id = f"edge_{i+1:03d}"
                port = start_port + i
                payload = {
                    "node_id": node_id,
                    "endpoint": f"localhost:{port}",
                    "cpus": 2,
                    "memory": "1g",
                }
                try:
                    r = requests.post(
                        f"{self.api_base}/nodes/register",
                        json=payload,
                        timeout=10,
                    )
                    if r.status_code == 200:
                        registered += 1
                    else:
                        print(f"register {node_id} failed: {r.status_code} {r.text}")
                except Exception as e:
                    print(f"register {node_id} error: {e}")
            print(f"Successfully registered {registered}/{num_edges} virtual edge nodes")
            return registered >= num_edges * 0.8
        except Exception as e:
            print(f"Failed to register virtual edges: {e}")
            return False

    def _spawn_real_edges(self, num_edges: int, start_port: int) -> bool:
        try:
            self.cleanup_processes()
            for i in range(num_edges):
                node_id = f"edge_{i+1:03d}"
                port = start_port + i
                cmd = [
                    "./deploy_edge.sh",
                    "--node-id", node_id,
                    "--central-url", self.central_url,
                    "--port", str(port),
                    "--cpus", "2",
                    "--memory", "1g",
                ]
                print(f"Starting {node_id} on port {port}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.edge_processes.append(process)
            print("Waiting for edge nodes to register...")
            time.sleep(max(2, num_edges // 5))
            response = requests.get(f"{self.api_base}/cluster/status")
            if response.status_code == 200:
                cluster_status = response.json()
                registered_edges = len(cluster_status.get('data', {}).get('cluster_info', {}).get('edge_nodes_info', []))
                print(f"Successfully registered {registered_edges}/{num_edges} edge nodes")
                return registered_edges >= num_edges * 0.8
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

    def get_all_assignment_algorithms(self):
        """Fetch all assignment algorithms exposed by the backend."""
        try:
            response = requests.get(f"{self.api_base}/all_assignment_algorithms", timeout=10)
            if response.status_code == 200:
                algorithms = response.json().get("data", {}).get("algorithms", []) or []
                return [str(alg) for alg in algorithms if alg]
            print(f"Failed to fetch assignment algorithms: {response.status_code} {response.text}")
            return []
        except Exception as e:
            print(f"Failed to fetch assignment algorithms: {e}")
            return []

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
                    # QoS metrics
                    "avg_latency_ms": float(m.get("avg_latency_ms", 0.0) or 0.0),
                    "p50_latency_ms": float(m.get("p50_latency_ms", 0.0) or 0.0),
                    "p95_latency_ms": float(m.get("p95_latency_ms", 0.0) or 0.0),
                    "p99_latency_ms": float(m.get("p99_latency_ms", 0.0) or 0.0),
                    "warm_rate": float(m.get("warm_rate", 0.0) or 0.0),
                    "rejected_count": int(float(m.get("rejected_count", 0) or 0)),
                    "pool_evictions": int(float(m.get("pool_evictions", 0) or 0)),
                    "pool_utilization_avg": float(m.get("pool_utilization_avg", 0.0) or 0.0),
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
            filename = self.current_csv_filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}.csv"

        print(f"Saving results to {filename}")
        if not self.results:
            print("No results to save")
            return

        fieldnames = self._csv_fieldnames()

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
                                # QoS
                                row["avg_latency_ms"] = v.get("avg_latency_ms", "")
                                row["p50_latency_ms"] = v.get("p50_latency_ms", "")
                                row["p95_latency_ms"] = v.get("p95_latency_ms", "")
                                row["p99_latency_ms"] = v.get("p99_latency_ms", "")
                                row["warm_rate"] = v.get("warm_rate", "")
                                row["rejected_count"] = v.get("rejected_count", "")
                                row["pool_evictions"] = v.get("pool_evictions", "")
                                row["pool_utilization_avg"] = v.get("pool_utilization_avg", "")
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
            user_ranges = [1000]  # 100 users
        if not edge_ranges:
            edge_ranges = [200]
        if not algorithms:
            algorithms = self.get_all_assignment_algorithms()
            if not algorithms:
                algorithms = ["greedy", "predictive"]
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
        csv_filename = self.init_results_csv()
        print(f"Streaming results to {csv_filename}")
        
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
                        self.append_result_to_csv(result, csv_filename)
                        
                        
                    except Exception as e:
                        print(f"Experiment failed: {e}")
                        failed = {
                            "timestamp": datetime.now().isoformat(),
                            "num_users": num_users,
                            "num_edges": num_edges,
                            "algorithm": algorithm,
                            "error": str(e),
                            "success": False
                        }
                        self.results.append(failed)
                        self.append_result_to_csv(failed, csv_filename)
                    
                    time.sleep(5)
            res = requests.post(f"{self.api_base}/reset_simulation")
        
            if res.status_code != 200:
                return {"error": "Failed to reset simulation"}
            else:
                print("Simulation reset successfully")
            self.cleanup_processes()
        total_time = time.time() - start_time
        csv_filename = self.current_csv_filename or csv_filename
        if csv_filename:
            print("Generating plots...")
            self.plot_comparison(csv_filename, save_path=f"experiment_comparison_{user_ranges[0]}.png")
        print(f"\nAll experiments completed in {total_time:.2f} seconds")
        successful = sum(1 for r in self.results if r.get('success', False))
        print(f"Experiment Summary: {successful}/{total_experiments} successful")


def main():
    central_url = os.getenv("CENTRAL_URL", "http://localhost:8000")
    runner = ExperimentRunner(central_url=central_url)

    # =====================================================================
    # EXPERIMENT MATRIX — edit these to change what gets run.
    # Each combination (num_users x num_edges x algorithm) = 1 experiment.
    # =====================================================================
    USER_RANGES = [100, 500, 1000, 5000]                                   # number of mobile users
    EDGE_RANGES = [10, 20, 100, 200]                                     # number of edge cloudlets
    ALGORITHMS  = []                                           # empty = fetch and run all backend algorithms
    DURATION_S  = 300                                          # seconds per experiment
    # =====================================================================

    runner.run_comprehensive_experiments(
        user_ranges=USER_RANGES,
        edge_ranges=EDGE_RANGES,
        algorithms=ALGORITHMS,
        experiment_duration=DURATION_S,
    )
    print("Experiment runner completed successfully!")


if __name__ == "__main__":
    main()
