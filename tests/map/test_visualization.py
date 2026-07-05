from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from scopp.map.grid import discretize_map
from scopp.map.io import load_map
from scopp.map.visualization import render_map

ROOT = Path(__file__).resolve().parents[2]


def test_render_returns_figure_without_changing_map() -> None:
    value = discretize_map(load_map(ROOT / "examples/maps/paper_like.yaml"))
    before = value.cells
    figure, axes = render_map(value)
    assert axes.get_aspect() == 1.0
    assert value.cells == before
    figure.clear()
