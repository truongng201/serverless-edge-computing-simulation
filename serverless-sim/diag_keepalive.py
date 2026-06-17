"""Fast diagnostic: greedy vs greedy+keep-alive, SAME steps, no sleep.

Drives the HTTP endpoints directly (skips run_simulation_workload's 1s/step
sleep) and prints warm/cold per execution step (step % 5 == 0) for both
variants side by side, so they can be compared at matching timesteps.

Expectation if keep-alive wiring is correct:
  - step 5 (first execution): warm counts ~equal (TTL irrelevant, same-step only)
  - later steps: keep-alive warm >= greedy warm (cross-step persistence helps)
"""
import requests

BASE = "http://localhost:8000/api/v1/central"
USERS, EDGES, STEPS, SEED = 100, 10, 20, 11


def run(algo):
    requests.post(f"{BASE}/reset_simulation", timeout=60)
    requests.post(f"{BASE}/assignment_algorithm", json={"algorithm": algo}, timeout=60)
    requests.post(f"{BASE}/set_dataset",
                  json={"dataset_name": "taxiD_Replay", "sample_size": USERS, "seed": SEED}, timeout=600)
    requests.post(f"{BASE}/start_simulation", timeout=60)
    per_step = {}
    for _ in range(STEPS):
        requests.get(f"{BASE}/get_all_users", timeout=600)
        m = requests.get(f"{BASE}/performance_metrics", timeout=600).json().get("data", {}) or {}
        wc, cc = int(float(m.get("warm_count", 0) or 0)), int(float(m.get("cold_count", 0) or 0))
        uc = int(float(m.get("unknown_count", 0) or 0))
        per_step[len(per_step) + 1] = (wc, cc, uc)
    requests.post(f"{BASE}/stop_simulation", timeout=60)
    return per_step


def main():
    print(f"Running greedy ({USERS}u/{EDGES}e/{STEPS} steps, seed={SEED})...")
    g = run("greedy")
    print("Running greedy + keep-alive...")
    k = run("greedy + keep-alive")

    print(f"\n{'poll':>5} | {'greedy (w/c/u)':>22} | {'keep-alive (w/c/u)':>22} | verdict")
    print("-" * 70)
    for poll in sorted(set(g) | set(k)):
        gw, gc, gu = g.get(poll, (0, 0, 0))
        kw, kc, ku = k.get(poll, (0, 0, 0))
        note = ""
        if (gw + gc) > 0 and (kw + kc) > 0:  # an execution step (status set)
            note = "keep-alive >= greedy OK" if kw >= gw else "!! keep-alive < greedy"
        print(f"{poll:>5} | {f'{gw}/{gc}/{gu}':>22} | {f'{kw}/{kc}/{ku}':>22} | {note}")

    # summary over execution steps only
    exec_polls = [p for p in g if (g[p][0] + g[p][1]) > 0 and (k.get(p, (0, 0))[0] + k.get(p, (0, 0))[1]) > 0]
    if exec_polls:
        gwarm = sum(g[p][0] for p in exec_polls) / len(exec_polls)
        kwarm = sum(k[p][0] for p in exec_polls) / len(exec_polls)
        print(f"\nAvg warm over {len(exec_polls)} execution polls: greedy={gwarm:.1f}  keep-alive={kwarm:.1f}")
        print("VERDICT:", "PASS — keep-alive warms more" if kwarm > gwarm
              else "FAIL — keep-alive does not increase warm reuse")


if __name__ == "__main__":
    main()
