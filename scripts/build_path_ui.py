"""Build a standalone interactive HTML UI for SCoPP assignments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp import ScoppConfig, ScoppPipeline
from scopp.config import ClusteringProfile, PathPlanningProfile
from scopp.ui import render_path_ui


def build_data(map_file: Path, config: ScoppConfig) -> dict[str, object]:
    result = ScoppPipeline(config).run_map(map_file)
    mapped, clustered, allocation, plan = result.mapped, result.clustered, result.allocation, result.plan
    owners = dict(allocation.owner_by_cell)
    return {
        "name": mapped.source.name,
        "profile": clustered.profile,
        "randomSeed": clustered.random_seed,
        "cellWidth": mapped.cell_width_m,
        "aoi": mapped.source.aoi.exterior,
        "noFly": [zone.exterior for zone in mapped.source.no_fly_zones],
        "conflicts": len(allocation.auction_decisions),
        "makespan": plan.makespan_distance_m,
        "totalDistance": plan.total_distance_m,
        "cells": [{"id": cell.id, "vertices": cell.vertices, "owner": owners[cell.id]} for cell in mapped.cells],
        "nodes": [{"index": path.cluster_index, "id": path.node_id, "start": path.start, "cells": len(path.cell_ids), "distance": path.distance_m, "cellIds": path.cell_ids, "motionCellIds": path.motion_cell_ids, "returnMotionIndex": path.return_motion_index, "waypoints": path.waypoints, "trajectory": path.trajectory} for path in plan.paths],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/path_ui.html"))
    parser.add_argument("--profile", choices=[item.value for item in ClusteringProfile], default=ClusteringProfile.DETERMINISTIC_LLOYD.value)
    parser.add_argument("--path-profile", choices=[item.value for item in PathPlanningProfile], default=PathPlanningProfile.PAPER_NN.value)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--bias", type=float, default=0.5)
    args = parser.parse_args()
    config = ScoppConfig.from_cli(args.profile, args.seed, args.bias, args.path_profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_path_ui(build_data(args.map_file, config)), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
