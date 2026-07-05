"""Render a SCoPP map definition to an image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp.map.grid import discretize_map
from scopp.map.io import load_map
from scopp.map.visualization import render_map


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("map.png"))
    parser.add_argument("--show-samples", action="store_true")
    args = parser.parse_args()
    result = discretize_map(load_map(args.map_file))
    figure, _ = render_map(result, show_samples=args.show_samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, bbox_inches="tight")
    print(f"wrote {args.output} ({len(result.cells)} cells, W={result.cell_width_m:.3f} m)")


if __name__ == "__main__":
    main()
