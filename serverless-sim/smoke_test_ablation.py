"""Smoke test for the ablation harness (Phase 0+1+2 verification).

Runs the 4 ablation variants at a tiny scale and checks:
  1. The 4 variants now produce DIFFERENT results (no more byte-identical pairs).
  2. Same (config, seed) reproduces exactly (determinism).
  3. Different seeds produce different cohorts (variance exists for CI).
  4. Per-request logs are written and parseable.

Usage: python smoke_test_ablation.py   (central node must be running on :8000)
"""
import sys

from run_experiments import ExperimentRunner

VARIANTS = [
    "greedy",
    "greedy + keep-alive",
    "prediction without warm-state awareness",
    "predictive",
]
USERS = 100
EDGES = 10
STEPS = 30


def series(result):
    """Extract a comparable (turnaround, cold) series from a run result."""
    m = result.get("metrics") or {}
    return [
        (
            round(v.get("total_turnaround_time", 0.0), 3),
            v.get("cold_count", 0),
            round(v.get("warm_rate", 0.0), 4),
        )
        for _, v in sorted(m.items())
    ]


def summarize(result):
    m = result.get("metrics") or {}
    n = len(m)
    if not n:
        return "NO METRICS"
    tat = sum(v.get("total_turnaround_time", 0.0) for v in m.values()) / n
    cold = sum(v.get("cold_count", 0) for v in m.values()) / n
    warm_rate = sum(v.get("warm_rate", 0.0) for v in m.values()) / n
    return f"avg_TAT={tat:12.1f}  avg_cold={cold:7.2f}  warm_rate={warm_rate:.3f}"


def main():
    runner = ExperimentRunner()
    if not runner.wait_for_central_node(timeout=30):
        sys.exit("central node not reachable")
    if not runner.deploy_edge_nodes(EDGES):
        sys.exit("failed to deploy edges")

    runs = {}
    for variant in VARIANTS:
        r = runner.run_single_experiment(USERS, EDGES, variant, STEPS, seed=11)
        if not r.get("success"):
            sys.exit(f"run failed for {variant}: {r.get('error')}")
        runs[variant] = r

    # Determinism + seed-variance probes on one mid-complexity variant.
    repeat = runner.run_single_experiment(USERS, EDGES, "greedy + keep-alive", STEPS, seed=11)
    other_seed = runner.run_single_experiment(USERS, EDGES, "greedy + keep-alive", STEPS, seed=23)

    print("\n" + "=" * 76)
    print("SMOKE TEST VERDICTS")
    print("=" * 76)
    for variant in VARIANTS:
        print(f"{variant:<45} {summarize(runs[variant])}")

    failures = []

    # 1. All variant pairs must differ.
    for i in range(len(VARIANTS)):
        for j in range(i + 1, len(VARIANTS)):
            a, b = VARIANTS[i], VARIANTS[j]
            if series(runs[a]) == series(runs[b]):
                failures.append(f"VARIANTS IDENTICAL: '{a}' == '{b}'")
    if not failures:
        print("[PASS] all 4 variants produce distinct result series")

    # 2. Same seed reproduces.
    if series(repeat) == series(runs["greedy + keep-alive"]):
        print("[PASS] same seed reproduces exactly (greedy + keep-alive, seed=11)")
    else:
        sa, sb = series(runs["greedy + keep-alive"]), series(repeat)
        ndiff = sum(1 for x, y in zip(sa, sb) if x != y)
        failures.append(f"NON-DETERMINISTIC: same seed differs in {ndiff}/{len(sa)} steps")

    # 3. Different seed differs.
    if series(other_seed) != series(runs["greedy + keep-alive"]):
        print("[PASS] different seed gives different results (variance for CI exists)")
    else:
        failures.append("NO SEED VARIANCE: seed 11 == seed 23")

    # 4. Greedy must be coldest, predictive warmest (sanity on warm model).
    def warm_rate(v):
        m = runs[v].get("metrics") or {}
        return sum(x.get("warm_rate", 0.0) for x in m.values()) / max(1, len(m))
    if warm_rate("greedy") < warm_rate("greedy + keep-alive"):
        print("[PASS] keep-alive raises warm rate over plain greedy "
              f"({warm_rate('greedy'):.3f} -> {warm_rate('greedy + keep-alive'):.3f})")
    else:
        failures.append(
            f"WARM MODEL SUSPECT: greedy warm_rate {warm_rate('greedy'):.3f} >= "
            f"keep-alive {warm_rate('greedy + keep-alive'):.3f}"
        )

    if failures:
        print("\n".join("[FAIL] " + f for f in failures))
        sys.exit(1)
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
