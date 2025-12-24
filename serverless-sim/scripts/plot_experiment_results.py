"""
Plot and summarize experiment CSV results produced by `serverless-sim/run_experiments.py`.

The CSV is expected to have columns:
  num_users,num_edges,algorithm,experiment_duration,total_experiment_time,timestep,total_turnaround_time

Notes
-----
`total_turnaround_time` in serverless-sim is computed as the SUM across all current users:
  propagation_delay + transmission_delay + computation_delay
(see `serverless-sim/central_node/control_layer/scheduler_module/scheduler.py`).

This script produces:
  - total turnaround time (sum over users) vs timestep
  - avg turnaround time per user vs timestep
  - (optional) predictive - greedy difference vs timestep
  - a small Markdown summary with clear units and statistics
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Series:
    timesteps: List[int]
    total_tat_ms: List[float]
    num_users: int
    num_edges: int


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if q <= 0:
        return xs[0]
    if q >= 100:
        return xs[-1]
    k = (len(xs) - 1) * (q / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    d0 = xs[f] * (c - k)
    d1 = xs[c] * (k - f)
    return d0 + d1


def load_csv(path: Path) -> Dict[str, Series]:
    series: Dict[str, List[Tuple[int, float]]] = {}
    num_users: Optional[int] = None
    num_edges: Optional[int] = None

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "num_users",
            "num_edges",
            "algorithm",
            "timestep",
            "total_turnaround_time",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")

        for row in reader:
            alg = row["algorithm"].strip()
            t = int(float(row["timestep"]))
            total = float(row["total_turnaround_time"])
            series.setdefault(alg, []).append((t, total))

            if num_users is None:
                num_users = int(float(row["num_users"]))
            if num_edges is None:
                num_edges = int(float(row["num_edges"]))

    if num_users is None or num_edges is None:
        raise ValueError("CSV appears empty")

    out: Dict[str, Series] = {}
    for alg, pairs in series.items():
        pairs_sorted = sorted(pairs, key=lambda x: x[0])
        out[alg] = Series(
            timesteps=[t for t, _ in pairs_sorted],
            total_tat_ms=[v for _, v in pairs_sorted],
            num_users=num_users,
            num_edges=num_edges,
        )
    return out


def compute_stats(values_ms: List[float]) -> Dict[str, float]:
    vals = [float(v) for v in values_ms if math.isfinite(float(v))]
    return {
        "mean_ms": mean(vals) if vals else float("nan"),
        "median_ms": median(vals) if vals else float("nan"),
        "p95_ms": _percentile(vals, 95.0),
        "p99_ms": _percentile(vals, 99.0),
        "min_ms": min(vals) if vals else float("nan"),
        "max_ms": max(vals) if vals else float("nan"),
    }


def _fmt_ms(ms: float) -> str:
    if not math.isfinite(ms):
        return "n/a"
    if ms >= 1000.0:
        return f"{ms:,.1f} ms ({ms/1000.0:,.2f} s)"
    return f"{ms:,.3f} ms"


def write_markdown_summary(
    out_path: Path,
    input_csv: Path,
    series: Dict[str, Series],
) -> None:
    lines: List[str] = []
    lines.append(f"# Experiment Summary: `{input_csv.name}`")
    lines.append("")
    # Pick a representative series for config fields
    any_series = next(iter(series.values()))
    lines.append(f"- Users: `{any_series.num_users}`")
    lines.append(f"- Edge nodes: `{any_series.num_edges}`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("- `total_turnaround_time` is the SUM across all current users (ms).")
    lines.append("- Below we also report `avg_per_user = total_turnaround_time / num_users` (ms/user).")
    lines.append("")

    algs = sorted(series.keys())
    for alg in algs:
        s = series[alg]
        total_stats = compute_stats(s.total_tat_ms)
        avg_ms = [v / max(1, s.num_users) for v in s.total_tat_ms]
        avg_stats = compute_stats(avg_ms)

        lines.append(f"### `{alg}`")
        lines.append("")
        lines.append("**Total TAT (sum over users)**")
        lines.append(f"- mean: `{_fmt_ms(total_stats['mean_ms'])}`")
        lines.append(f"- median: `{_fmt_ms(total_stats['median_ms'])}`")
        lines.append(f"- p95: `{_fmt_ms(total_stats['p95_ms'])}`")
        lines.append(f"- p99: `{_fmt_ms(total_stats['p99_ms'])}`")
        lines.append(f"- min/max: `{_fmt_ms(total_stats['min_ms'])}` / `{_fmt_ms(total_stats['max_ms'])}`")
        lines.append("")
        lines.append("**Avg per user (ms/user)**")
        lines.append(f"- mean: `{_fmt_ms(avg_stats['mean_ms'])}`")
        lines.append(f"- median: `{_fmt_ms(avg_stats['median_ms'])}`")
        lines.append(f"- p95: `{_fmt_ms(avg_stats['p95_ms'])}`")
        lines.append(f"- p99: `{_fmt_ms(avg_stats['p99_ms'])}`")
        lines.append(f"- min/max: `{_fmt_ms(avg_stats['min_ms'])}` / `{_fmt_ms(avg_stats['max_ms'])}`")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot(
    series: Dict[str, Series],
    out_dir: Path,
    title: str,
    show: bool,
    force_svg: bool,
) -> None:
    def _plot_svg() -> None:
        def _svg_escape(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            )

        def _fmt(x: float) -> str:
            return f"{x:,.0f}"

        def _write_svg(
            out_path: Path,
            xs_by_alg: Dict[str, List[int]],
            ys_by_alg: Dict[str, List[float]],
            y_label: str,
            title_line: str,
            colors: Dict[str, str],
        ) -> None:
            width, height = 1100, 520
            margin_l, margin_r, margin_t, margin_b = 90, 20, 55, 70
            plot_w = width - margin_l - margin_r
            plot_h = height - margin_t - margin_b

            # Domain/range
            all_x = [x for xs in xs_by_alg.values() for x in xs]
            all_y = [y for ys in ys_by_alg.values() for y in ys if math.isfinite(y)]
            if not all_x or not all_y:
                return
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            if y_max <= y_min:
                y_max = y_min + 1.0

            def sx(x: float) -> float:
                if x_max == x_min:
                    return margin_l + plot_w / 2.0
                return margin_l + (x - x_min) * plot_w / (x_max - x_min)

            def sy(y: float) -> float:
                return margin_t + (y_max - y) * plot_h / (y_max - y_min)

            # Ticks
            x_ticks = 6
            y_ticks = 6
            x_tick_vals = [
                round(x_min + i * (x_max - x_min) / (x_ticks - 1))
                for i in range(x_ticks)
            ]
            y_tick_vals = [
                y_min + i * (y_max - y_min) / (y_ticks - 1) for i in range(y_ticks)
            ]

            # Build SVG
            parts: List[str] = []
            parts.append(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            )
            parts.append('<rect x="0" y="0" width="100%" height="100%" fill="white"/>')
            parts.append(
                f'<text x="{width/2:.1f}" y="28" text-anchor="middle" font-family="Arial" font-size="18" fill="#111">{_svg_escape(title_line)}</text>'
            )

            # Grid + y ticks
            for v in y_tick_vals:
                yy = sy(v)
                parts.append(
                    f'<line x1="{margin_l}" y1="{yy:.2f}" x2="{width-margin_r}" y2="{yy:.2f}" stroke="#e6e6e6" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{margin_l-10}" y="{yy+4:.2f}" text-anchor="end" font-family="Arial" font-size="12" fill="#333">{_svg_escape(_fmt(v))}</text>'
                )

            # x ticks
            for v in x_tick_vals:
                xx = sx(v)
                parts.append(
                    f'<line x1="{xx:.2f}" y1="{margin_t}" x2="{xx:.2f}" y2="{height-margin_b}" stroke="#f0f0f0" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{xx:.2f}" y="{height-margin_b+20}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">{v}</text>'
                )

            # Axes
            parts.append(
                f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{height-margin_b}" stroke="#111" stroke-width="1.5"/>'
            )
            parts.append(
                f'<line x1="{margin_l}" y1="{height-margin_b}" x2="{width-margin_r}" y2="{height-margin_b}" stroke="#111" stroke-width="1.5"/>'
            )
            # Labels
            parts.append(
                f'<text x="{width/2:.1f}" y="{height-25}" text-anchor="middle" font-family="Arial" font-size="14" fill="#111">Timestep</text>'
            )
            parts.append(
                f'<text x="22" y="{height/2:.1f}" transform="rotate(-90, 22, {height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="14" fill="#111">{_svg_escape(y_label)}</text>'
            )

            # Lines
            for alg, xs in xs_by_alg.items():
                ys = ys_by_alg.get(alg, [])
                if not xs or not ys or len(xs) != len(ys):
                    continue
                pts = []
                for x, y in zip(xs, ys):
                    if not math.isfinite(y):
                        continue
                    pts.append(f"{sx(x):.2f},{sy(y):.2f}")
                if not pts:
                    continue
                color = colors.get(alg, "#1f77b4")
                parts.append(
                    f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/>'
                )

            # Legend
            lx, ly = width - margin_r - 220, margin_t + 10
            parts.append(f'<rect x="{lx}" y="{ly-18}" width="210" height="{20+18*len(xs_by_alg)}" fill="white" stroke="#ddd"/>')
            y0 = ly
            for alg in xs_by_alg.keys():
                color = colors.get(alg, "#1f77b4")
                parts.append(f'<line x1="{lx+12}" y1="{y0-5}" x2="{lx+32}" y2="{y0-5}" stroke="{color}" stroke-width="3"/>')
                parts.append(f'<text x="{lx+40}" y="{y0-1}" font-family="Arial" font-size="12" fill="#111">{_svg_escape(alg)}</text>')
                y0 += 18

            parts.append("</svg>")
            out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")

        out_dir.mkdir(parents=True, exist_ok=True)
        colors = {"predictive": "#d62728", "greedy": "#1f77b4"}

        xs_by_alg = {alg: s.timesteps for alg, s in series.items()}
        ys_total = {alg: s.total_tat_ms for alg, s in series.items()}
        _write_svg(
            out_dir / "total_turnaround_time_ms.svg",
            xs_by_alg,
            ys_total,
            "Total turnaround time (ms)",
            f"{title} — Total turnaround time (sum over users)",
            colors,
        )

        ys_avg = {alg: [v / max(1, s.num_users) for v in s.total_tat_ms] for alg, s in series.items()}
        _write_svg(
            out_dir / "avg_turnaround_time_ms_per_user.svg",
            xs_by_alg,
            ys_avg,
            "Avg turnaround time (ms/user)",
            f"{title} — Avg turnaround time per user",
            colors,
        )

        if "predictive" in series and "greedy" in series:
            sp = series["predictive"]
            sg = series["greedy"]
            g_map = dict(zip(sg.timesteps, sg.total_tat_ms))
            xs = []
            ys = []
            for t, v in zip(sp.timesteps, sp.total_tat_ms):
                if t in g_map:
                    xs.append(t)
                    ys.append(v - g_map[t])
            _write_svg(
                out_dir / "delta_predictive_minus_greedy_ms.svg",
                {"predictive - greedy": xs},
                {"predictive - greedy": ys},
                "Δ total turnaround time (ms)",
                f"{title} — Difference (predictive - greedy)",
                {"predictive - greedy": "#8b0000"},
            )

    if force_svg:
        _plot_svg()
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
    except Exception:
        # Fall back to a pure-SVG renderer (no numpy/matplotlib dependency).
        _plot_svg()
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    def fmt_thousands(x, _pos):
        return f"{x:,.0f}"

    # Plot 1: total turnaround time (sum)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    for alg, s in sorted(series.items()):
        ax.plot(s.timesteps, s.total_tat_ms, label=alg, linewidth=2)
    ax.set_title(f"{title} — Total turnaround time (sum over users)")
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Total turnaround time (ms)")
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_thousands))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "total_turnaround_time_ms.png")
    plt.close(fig)

    # Plot 2: avg per-user turnaround time
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    for alg, s in sorted(series.items()):
        avg_ms = [v / max(1, s.num_users) for v in s.total_tat_ms]
        ax.plot(s.timesteps, avg_ms, label=alg, linewidth=2)
    ax.set_title(f"{title} — Avg turnaround time per user")
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Avg turnaround time (ms/user)")
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_thousands))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "avg_turnaround_time_ms_per_user.png")
    plt.close(fig)

    # Plot 3: predictive - greedy difference (if both exist)
    if "predictive" in series and "greedy" in series:
        s_p = series["predictive"]
        s_g = series["greedy"]
        # Align by timestep (take intersection)
        g_map = dict(zip(s_g.timesteps, s_g.total_tat_ms))
        xs = []
        ys = []
        for t, v in zip(s_p.timesteps, s_p.total_tat_ms):
            if t in g_map:
                xs.append(t)
                ys.append(v - g_map[t])

        fig, ax = plt.subplots(figsize=(10, 4), dpi=160)
        ax.axhline(0.0, color="black", linewidth=1, alpha=0.6)
        ax.plot(xs, ys, label="predictive - greedy", linewidth=2, color="#8b0000")
        ax.set_title(f"{title} — Difference (predictive - greedy)")
        ax.set_xlabel("Timestep")
        ax.set_ylabel("Δ total turnaround time (ms)")
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_thousands))
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "delta_predictive_minus_greedy_ms.png")
        plt.close(fig)

    if show:
        # Re-open a compact summary figure for interactive use.
        import matplotlib.pyplot as plt  # type: ignore

        fig, ax = plt.subplots(figsize=(10, 4), dpi=130)
        for alg, s in sorted(series.items()):
            avg_ms = [v / max(1, s.num_users) for v in s.total_tat_ms]
            ax.plot(s.timesteps, avg_ms, label=alg, linewidth=2)
        ax.set_title(f"{title} — Avg per user")
        ax.set_xlabel("Timestep")
        ax.set_ylabel("ms/user")
        ax.grid(True, alpha=0.25)
        ax.legend()
        plt.show()


def main() -> int:
    ap = argparse.ArgumentParser(description="Plot serverless-sim experiment CSV results.")
    ap.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to experiment_results_*.csv",
    )
    ap.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Output directory for plots + summary.md (default: ./plots/<csv_stem>/)",
    )
    ap.add_argument(
        "--title",
        type=str,
        default=None,
        help="Plot title (default: CSV stem).",
    )
    ap.add_argument("--show", action="store_true", help="Show interactive plots.")
    ap.add_argument(
        "--force-svg",
        action="store_true",
        help="Skip matplotlib and render static SVGs only (useful when numpy/matplotlib are broken).",
    )
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    out_dir = Path(args.out_dir) if args.out_dir else (Path("plots") / csv_path.stem)
    title = args.title or csv_path.stem

    series = load_csv(csv_path)
    plot(series, out_dir, title=title, show=bool(args.show), force_svg=bool(args.force_svg))
    write_markdown_summary(out_dir / "summary.md", csv_path, series)

    print(f"Wrote plots to: {out_dir.resolve()}")
    print(f"Wrote summary to: {(out_dir / 'summary.md').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
