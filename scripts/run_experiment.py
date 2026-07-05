"""Run one reproducible SCoPP experiment and write its metrics as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp.experiment import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("experiment.json"))
    parser.add_argument("--bias", type=float, default=0.5)
    args = parser.parse_args()
    report = run_experiment(args.map_file, auction_bias=args.bias)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"cells={report.cell_count} nodes={report.node_count} conflicts={report.conflict_cell_count}")
    print(f"makespan={report.makespan_distance_m:.3f}m workload_range={report.cell_count_range} total_time={report.timings.total_s:.6f}s")


if __name__ == "__main__":
    main()
