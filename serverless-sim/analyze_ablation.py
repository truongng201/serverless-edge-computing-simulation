"""Aggregate ablation-grid results into Table IV (mean +/- 95% CI over seeds).

Input : experiment_results_<ts>.csv produced by run_experiments.py
        (one row per timestep per run; includes the `seed` column).
Output: - table_iv.csv           machine-readable aggregate
        - printed Table IV       mean +/- CI per (variant, user scale)
        - optional LaTeX rows    --latex

Per-run scalar = mean over timesteps (turnaround, energy, warm_rate)
                 or sum over timesteps (cold starts).
CI uses Student-t with df = n_seeds - 1 (t = 2.776 for n=5), NOT z=1.96.

Per-request latency files (request_logs/req_*.csv.gz) are aggregated separately
with --requests: p50/p95/p99, jitter (std of per-user latency over time), and
a pooled CDF dump for plotting.

Usage:
  python analyze_ablation.py experiment_results_YYYYMMDD_HHMMSS.csv
  python analyze_ablation.py results.csv --latex
  python analyze_ablation.py results.csv --requests request_logs --cdf-out cdf_data.csv
"""
import argparse
import csv
import glob
import gzip
import math
import os
import re
import sys
from collections import defaultdict

# two-sided 95% Student-t critical values by df
T_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228}

VARIANT_ORDER = [
    "greedy",
    "greedy + keep-alive",
    "prediction without warm-state awareness",
    "predictive",
]

METRICS = {
    # column -> (aggregation over timesteps, pretty name)
    "total_turnaround_time": ("mean", "Turnaround (ms, step mean)"),
    "cold_count": ("sum", "Cold starts (total)"),
    "total_energy_j": ("sum", "Energy (J, total)"),
    "warm_rate": ("mean", "Warm rate"),
    "p95_latency_ms": ("mean", "p95 latency (ms)"),
    "p99_latency_ms": ("mean", "p99 latency (ms)"),
}


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def mean_ci(values):
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"), 0)
    m = sum(values) / n
    if n == 1:
        return (m, float("nan"), 1)
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    t = T_95.get(n - 1, 1.96)
    return (m, t * math.sqrt(var / n), n)


def load_runs(path):
    """runs[(users, edges, algorithm, seed)][metric] = per-run scalar"""
    per_step = defaultdict(lambda: defaultdict(list))
    skipped_warmup = 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                users = int(row["num_users"])
                edges = int(row["num_edges"])
            except (TypeError, ValueError, KeyError):
                continue
            algo = (row.get("algorithm") or "").strip()
            seed = (row.get("seed") or "").strip() or "NA"
            if not algo or row.get("timestep", "") == "":
                continue
            # Skip warm-up steps before the first execution (execution runs only
            # every 5 sim steps; earlier steps have container_status="unknown"
            # and don't represent a measured request outcome).
            unknown = fnum(row.get("unknown_count"))
            if unknown is not None and unknown > 0:
                skipped_warmup += 1
                continue
            key = (users, edges, algo, seed)
            for col in METRICS:
                v = fnum(row.get(col))
                if v is not None:
                    per_step[key][col].append(v)

    runs = {}
    for key, cols in per_step.items():
        runs[key] = {}
        for col, (agg, _) in METRICS.items():
            vals = cols.get(col, [])
            if not vals:
                continue
            runs[key][col] = sum(vals) if agg == "sum" else sum(vals) / len(vals)
    if skipped_warmup:
        print(f"(skipped {skipped_warmup} warm-up rows with unknown_count>0)")
    return runs


def aggregate(runs):
    """table[(users, edges, algo)][metric] = (mean, ci, n_seeds)"""
    by_config = defaultdict(lambda: defaultdict(list))
    for (users, edges, algo, _seed), metrics in runs.items():
        for col, val in metrics.items():
            by_config[(users, edges, algo)][col].append(val)
    return {
        cfg: {col: mean_ci(vals) for col, vals in cols.items()}
        for cfg, cols in by_config.items()
    }


def print_table(table, latex=False):
    users_scales = sorted({u for (u, _, _) in table})
    edges_set = sorted({e for (_, e, _) in table})
    algos_present = {a for (_, _, a) in table}
    algos = [a for a in VARIANT_ORDER if a in algos_present]
    algos += sorted(algos_present - set(algos))

    for edges in edges_set:
        print(f"\n{'=' * 100}\nTABLE IV — topology: {edges} cloudlets   (mean ± 95% CI over seeds, Student-t)\n{'=' * 100}")
        for col, (_, pretty) in METRICS.items():
            print(f"\n--- {pretty} ---")
            header = f"{'variant':<46}" + "".join(f"{u:>13}" for u in users_scales)
            print(header)
            for algo in algos:
                cells = []
                for u in users_scales:
                    entry = table.get((u, edges, algo), {}).get(col)
                    if entry is None:
                        cells.append(f"{'—':>13}")
                    else:
                        m, ci, n = entry
                        cells.append(f"{m:>9.4g}±{ci:<4.2g}" if ci == ci else f"{m:>11.4g} ?")
                print(f"{algo:<46}" + "".join(cells))

        if latex:
            print("\n--- LaTeX rows (turnaround / cold / energy) ---")
            for algo in algos:
                parts = [algo.replace("&", r"\&")]
                for u in users_scales:
                    for col in ("total_turnaround_time", "cold_count", "total_energy_j"):
                        entry = table.get((u, edges, algo), {}).get(col)
                        if entry:
                            m, ci, _ = entry
                            parts.append(f"${m:.4g} \\pm {ci:.2g}$")
                        else:
                            parts.append("--")
                print(" & ".join(parts) + r" \\")


def write_csv(table, out_path):
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num_users", "num_edges", "algorithm", "metric", "mean", "ci95", "n_seeds"])
        for (users, edges, algo), cols in sorted(table.items()):
            for col, (m, ci, n) in cols.items():
                w.writerow([users, edges, algo, col, f"{m:.6g}", f"{ci:.6g}" if ci == ci else "", n])
    print(f"\nWrote {out_path}")


# ----------------------------------------------------------------- requests
REQ_NAME = re.compile(r"req_(?P<algo>.+)_u(?P<users>\d+)_e(?P<edges>\d+)_s(?P<seed>[^_]+)_\d+_\d+\.csv\.gz$")


def analyze_requests(log_dir, cdf_out=None):
    """Per-request analysis: percentiles + jitter per run; optional pooled CDF dump."""
    files = sorted(glob.glob(os.path.join(log_dir, "req_*.csv.gz")))
    if not files:
        print(f"No request logs found under {log_dir}")
        return
    print(f"\n{'=' * 100}\nPER-REQUEST ANALYSIS — {len(files)} run logs\n{'=' * 100}")
    print(f"{'run':<60}{'n_req':>9}{'p50':>9}{'p95':>9}{'p99':>10}{'jitter':>9}")

    cdf_rows = []
    for path in files:
        name = os.path.basename(path)
        m = REQ_NAME.search(name)
        lat = []
        per_user = defaultdict(list)
        try:
            with gzip.open(path, "rt", newline="") as fh:
                for row in csv.DictReader(fh):
                    v = fnum(row.get("total_ms"))
                    if v is None:
                        continue
                    lat.append(v)
                    per_user[row.get("user_id")].append(v)
        except (EOFError, OSError) as exc:
            print(f"{name:<60} UNREADABLE ({exc})")
            continue
        if not lat:
            print(f"{name:<60} EMPTY")
            continue
        lat.sort()
        n = len(lat)
        pct = lambda p: lat[min(n - 1, int(round(p / 100.0 * (n - 1))))]
        # jitter = mean over users of the std of that user's latency across steps
        stds = []
        for series in per_user.values():
            if len(series) >= 2:
                mu = sum(series) / len(series)
                stds.append(math.sqrt(sum((x - mu) ** 2 for x in series) / (len(series) - 1)))
        jitter = sum(stds) / len(stds) if stds else float("nan")
        print(f"{name:<60}{n:>9}{pct(50):>9.1f}{pct(95):>9.1f}{pct(99):>10.1f}{jitter:>9.1f}")

        if cdf_out and m:
            # decimate to <=2000 quantile points per run for plottable CDFs
            step = max(1, n // 2000)
            for i in range(0, n, step):
                cdf_rows.append([m["algo"], m["users"], m["edges"], m["seed"],
                                 f"{lat[i]:.3f}", f"{(i + 1) / n:.6f}"])

    if cdf_out and cdf_rows:
        with open(cdf_out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["algorithm", "num_users", "num_edges", "seed", "latency_ms", "cdf"])
            w.writerows(cdf_rows)
        print(f"\nWrote CDF data: {cdf_out} ({len(cdf_rows)} points)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_csv", nargs="?", help="experiment_results_*.csv from run_experiments.py")
    ap.add_argument("--out", default="table_iv.csv", help="aggregate CSV output path")
    ap.add_argument("--latex", action="store_true", help="also print LaTeX table rows")
    ap.add_argument("--requests", metavar="DIR", help="per-request log dir (request_logs)")
    ap.add_argument("--cdf-out", metavar="CSV", help="write pooled CDF quantiles for plotting")
    args = ap.parse_args()

    if not args.results_csv and not args.requests:
        ap.error("give a results CSV and/or --requests DIR")

    if args.results_csv:
        runs = load_runs(args.results_csv)
        if not runs:
            sys.exit(f"no usable rows in {args.results_csv}")
        seeds_per_cfg = defaultdict(set)
        for (u, e, a, s) in runs:
            seeds_per_cfg[(u, e, a)].add(s)
        n_min = min(len(s) for s in seeds_per_cfg.values())
        print(f"Loaded {len(runs)} runs over {len(seeds_per_cfg)} configs "
              f"(min seeds per config: {n_min})")
        table = aggregate(runs)
        print_table(table, latex=args.latex)
        write_csv(table, args.out)

    if args.requests:
        analyze_requests(args.requests, cdf_out=args.cdf_out)


if __name__ == "__main__":
    main()
