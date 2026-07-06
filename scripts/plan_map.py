"""Run the implemented SCoPP pipeline and render the resulting paths."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp import ClusteringProfile, ScoppConfig, ScoppPipeline
from scopp.map.visualization import render_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("plan.png"))
    parser.add_argument("--profile", choices=[item.value for item in ClusteringProfile], default=ClusteringProfile.DETERMINISTIC_LLOYD.value)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    config = ScoppConfig.from_cli(args.profile, args.seed)
    result = ScoppPipeline(config).run_map(args.map_file)
    figure, _ = render_plan(result.mapped, result.allocation, result.plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, bbox_inches="tight")
    print(f"wrote {args.output}")
    print(f"cells={len(result.mapped.cells)} conflicts={len(result.allocation.auction_decisions)} makespan={result.plan.makespan_distance_m:.3f}m total={result.plan.total_distance_m:.3f}m")
    for path in result.plan.paths:
        print(f"{path.node_id}: cells={len(path.cell_ids)} distance={path.distance_m:.3f}m")


if __name__ == "__main__":
    main()
