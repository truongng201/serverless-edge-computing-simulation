"""Measure handoffs (cloudlet switches) vs number of edges.

For each edge count, run greedy (no predictor needed), 100 users, fixed seed, and
count how many times each user's assigned_node_id CHANGES step-to-step (= a handoff).
Drives endpoints directly (no 1s/step sleep).
"""
import requests
from collections import defaultdict

B = "http://localhost:8000/api/v1/central"
USERS, STEPS, SEED, ALGO = 100, 40, 11, "greedy"


def run(num_edges):
    # register exactly num_edges virtual edges
    requests.delete(f"{B}/nodes", timeout=30)
    for i in range(num_edges):
        requests.post(f"{B}/nodes/register",
                      json={"node_id": f"edge_{i+1:03d}", "endpoint": f"localhost:{5001+i}",
                            "cpus": 2, "memory": "1g"}, timeout=15)
    requests.post(f"{B}/reset_simulation", timeout=60)
    requests.post(f"{B}/assignment_algorithm", json={"algorithm": ALGO}, timeout=60)
    requests.post(f"{B}/set_dataset",
                  json={"dataset_name": "taxiD_Replay", "sample_size": USERS, "seed": SEED}, timeout=600)
    requests.post(f"{B}/start_simulation", timeout=60)

    prev = {}
    handoffs = 0
    assigned_steps = 0
    for _ in range(STEPS):
        r = requests.get(f"{B}/get_all_users", timeout=600).json().get("data", {})
        users = r.get("users") if isinstance(r, dict) else None
        if not users:
            continue
        for u in users:
            uid = u.get("user_id"); node = u.get("assigned_node_id")
            if node is None:
                continue
            assigned_steps += 1
            if uid in prev and prev[uid] != node:
                handoffs += 1
            prev[uid] = node
    requests.post(f"{B}/stop_simulation", timeout=60)
    return handoffs, assigned_steps


print(f"{ALGO}, {USERS} users, {STEPS} steps, seed={SEED}\n")
print(f"{'edges':>6} | {'handoffs':>9} | {'handoff rate (per user-step)':>28}")
print("-" * 52)
for e in [10, 50, 100]:
    h, n = run(e)
    rate = h / n if n else 0
    print(f"{e:>6} | {h:>9} | {rate:>28.4f}")
