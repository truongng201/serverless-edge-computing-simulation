import time

def simulate_cpu(seconds=5):
    end = time.time() + seconds
    x = 0
    while time.time() < end:
        x += 1
    return x

def handler(event, context):
    print("Simulate an simple execution with sleeping")
    work = simulate_cpu(5)
    return f"CPU work finished. Iterations: {work}"