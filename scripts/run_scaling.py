"""Run node-count scaling evaluation and write CSV plus a chart."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp.map.io import load_map
from scopp.scaling import run_scaling_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("scaling.csv"))
    parser.add_argument("--plot", type=Path, default=Path("scaling.png"))
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    report = run_scaling_experiment(load_map(args.map_file), repetitions=args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(point) for point in report.points]
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = [point.node_count for point in report.points]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    axes[0].plot(counts, [point.makespan_distance_m for point in report.points], marker="o")
    axes[0].set(xlabel="node count", ylabel="makespan distance (m)", title="Mission distance")
    axes[0].grid(alpha=0.3)
    axes[1].errorbar(counts, [point.mean_runtime_s for point in report.points], yerr=[point.runtime_std_s for point in report.points], marker="o", capsize=3)
    axes[1].set(xlabel="node count", ylabel="runtime (s)", title="Computation time")
    axes[1].grid(alpha=0.3)
    fig.suptitle(report.map_name)
    fig.tight_layout()
    args.plot.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.plot, dpi=160, bbox_inches="tight")
    print(f"wrote {args.output} and {args.plot}")


if __name__ == "__main__":
    main()
