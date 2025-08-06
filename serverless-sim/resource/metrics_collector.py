import psutil
import time

class ServerlessMetrics:
    def __init__(self):
        pass

    def display(self):
        while True:
            # CPU usage
            cpu = psutil.cpu_percent(interval=1)
            bar = '|' * int(cpu // 2)
            print(f"Overall CPU Usage: {cpu:.1f}% {bar}")
            # Memory info
            mem = psutil.virtual_memory()
            used = mem.used / 1024**2
            total = mem.total / 1024**2
            print("Memory Usage:")
            print(f"Used: {used:.1f} MB / {total:.1f} MB ({mem.percent:.1f}%)")
            
            time.sleep(10)
    
    def collect_metrics(self):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        metrics = {
            "cpu_usage": cpu,
            "memory_used": mem.used / 1024**2,  # Convert to MB
            "memory_total": mem.total / 1024**2,  # Convert to MB
            "memory_percent": mem.percent
        }
        return metrics