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
        # dataset_name = 'taxiD_Replay'
        dataset_name = f'random_generated'
        try:
            print(f"Setting dataset '{dataset_name}' with num_users={num_users}")
            payload = {"dataset_name": dataset_name, "sample_size": num_users}
            response = requests.post(f"{self.api_base}/set_dataset", json=payload, timeout=50)
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
                metrics[timestep + 1] = metrics_response.json().get('data', {}).get("total_turnaround_time", 0)
                print(f"Timestep {timestep + 1}: Total Turnaround Time = {metrics[timestep + 1]}")
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
            return {"error": f"Failed to set dataset random_generated for {num_users} users"}
        
        metrics = self.run_simulation_workload(duration=experiment_duration)
        
        experiment_time = time.time() - experiment_start
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "num_users": num_users,
            "num_edges": num_edges,
            "algorithm": algorithm,
            "experiment_duration": experiment_duration,
            "total_experiment_time": experiment_time,
            "metrics": metrics,
            "success": True if metrics and len(metrics) > 0 else False
        }
        
        print(f"Experiment completed in {experiment_time:.2f} seconds")
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
    
    def plot_comparison(self, csv_filename: str = None, save_path: str = None, show: bool = True):
        """Plot algorithm comparison in two separate figures with better zoom"""
        if csv_filename is None:
            import glob
            csv_files = glob.glob("experiment_results_*.csv")
            if not csv_files:
                print("No CSV files found to plot")
                return
            csv_filename = max(csv_files, key=os.path.getctime)
            print(f"Using most recent CSV: {csv_filename}")

        data = self.load_results_from_csv(csv_filename)
        if not data:
            print("No data to plot")
            return

        # Load experiment times from CSV
        exp_times = {}  # (users, edges, algorithm) -> total_experiment_time
        try:
            with open(csv_filename, newline='') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    try:
                        users = int(r.get("num_users", 0))
                        edges = int(r.get("num_edges", 0))
                        alg = r.get("algorithm", "").strip()
                        exp_time = float(r.get("total_experiment_time", 0))
                        exp_times[(users, edges, alg)] = exp_time
                    except:
                        continue
        except:
            pass

        combos = sorted(data.keys())
        n = len(combos)
        cols = min(4, n)  # More columns for better layout
        rows = math.ceil(n / cols)

        # ===== FIGURE 1: TURNAROUND TIMES =====
        plt.style.use("seaborn-v0_8-darkgrid")
        fig1, axes1 = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), squeeze=False)

        for idx, combo in enumerate(combos):
            r = idx // cols
            c = idx % cols
            ax = axes1[r][c]
            
            algs = data[combo]
            if not algs:
                ax.set_visible(False)
                continue
                
            all_timesteps = set()
            for alg in algs:
                all_timesteps.update(algs[alg].keys())
            if not all_timesteps:
                ax.set_visible(False)
                continue
            all_timesteps = sorted(all_timesteps)
            
            # Get all values to determine proper zoom range
            all_values = []
            for alg, od in algs.items():
                all_values.extend(od.values())
            if not all_values:
                continue
                
            min_val = min(all_values)
            max_val = max(all_values)
            
            # Plot with thicker lines and larger markers
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            for i, (alg, od) in enumerate(algs.items()):
                xs = list(od.keys())
                ys = list(od.values())
                if not xs:
                    continue
                ax.plot(xs, ys, marker='o', linewidth=3, markersize=8, 
                       label=alg, color=colors[i % len(colors)])

            ax.set_title(f"Users={combo[0]}, Edges={combo[1]}", fontsize=14, fontweight='bold')
            ax.set_xlabel("Timestep", fontsize=12)
            ax.set_ylabel("Total Turnaround Time", fontsize=12)
            ax.set_xticks(all_timesteps)
            
            # Better zoom: focus on the actual data range
            if max_val > min_val:
                range_val = max_val - min_val
                margin = max(range_val * 0.05, abs(min_val) * 0.0001)  # At least 0.01% margin
                ax.set_ylim(min_val - margin, max_val + margin)
            
            # Format y-axis with more precision
            if min_val > 100:
                from matplotlib.ticker import FuncFormatter
                def format_func(x, p):
                    return f'{x:.3f}'
                ax.yaxis.set_major_formatter(FuncFormatter(format_func))
            
            ax.grid(True, alpha=0.4)
            ax.legend(fontsize=11, loc='best')
            ax.tick_params(axis='both', which='major', labelsize=10)

        # Hide unused subplots
        for idx in range(len(combos), rows * cols):
            r = idx // cols
            c = idx % cols
            axes1[r][c].set_visible(False)

        fig1.suptitle("Algorithm Performance: Total Turnaround Time Comparison", 
                     fontsize=18, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.95])

        # ===== FIGURE 2: EXPERIMENT DURATION =====
        fig2, axes2 = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), squeeze=False)

        for idx, combo in enumerate(combos):
            r = idx // cols
            c = idx % cols  
            ax = axes2[r][c]
            
            # Get experiment times for this combo
            exp_data = []
            exp_labels = []
            exp_colors = []
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            
            for i, alg in enumerate(sorted(data[combo].keys()) if combo in data else []):
                key = (combo[0], combo[1], alg)
                if key in exp_times:
                    exp_data.append(exp_times[key])
                    exp_labels.append(alg)
                    exp_colors.append(colors[i % len(colors)])
            
            if exp_data:
                bars = ax.bar(exp_labels, exp_data, alpha=0.8, color=exp_colors, width=0.6)
                ax.set_title(f"Users={combo[0]}, Edges={combo[1]}", fontsize=14, fontweight='bold')
                ax.set_ylabel("Experiment Time (seconds)", fontsize=12)
                ax.tick_params(axis='x', rotation=0, labelsize=11)
                ax.tick_params(axis='y', labelsize=10)
                
                # Add value labels on bars with better formatting
                for bar, val in zip(bars, exp_data):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                          f'{val:.1f}s', ha='center', va='bottom', fontsize=11, fontweight='bold')
                
                # Set y-limit with some margin
                max_time = max(exp_data)
                ax.set_ylim(0, max_time * 1.15)
                ax.grid(True, alpha=0.3, axis='y')
            else:
                ax.set_visible(False)

        # Hide unused subplots  
        for idx in range(len(combos), rows * cols):
            r = idx // cols
            c = idx % cols
            axes2[r][c].set_visible(False)

        fig2.suptitle("Algorithm Performance: Experiment Duration Comparison", 
                     fontsize=18, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.95])

        # Save both figures
        if save_path:
            base_name = save_path.replace('.png', '')
            turnaround_path = f"{base_name}_turnaround.png"
            duration_path = f"{base_name}_duration.png"
            
            fig1.savefig(turnaround_path, dpi=300, bbox_inches='tight')
            fig2.savefig(duration_path, dpi=300, bbox_inches='tight')
            print(f"Saved turnaround plot to {turnaround_path}")
            print(f"Saved duration plot to {duration_path}")
        
    
    def run_comprehensive_experiments(self, user_ranges = [], edge_ranges = [], algorithms = [], experiment_duration = 50):
        if not user_ranges:
            user_ranges = [100, 200]
        if not edge_ranges:
            edge_ranges = [10, 20]
        if not algorithms:
            algorithms = ["predictive", "greedy"]
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
        csv_filename = self.save_results_to_csv()
        if csv_filename:
            print("Generating plots...")
            self.plot_comparison(csv_filename, save_path=f"experiment_comparison_{user_ranges[0]}.png")
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