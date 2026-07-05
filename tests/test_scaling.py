from pathlib import Path

import pytest

from scopp.map.io import load_map
from scopp.scaling import run_scaling_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_scaling_runs_all_available_node_counts() -> None:
    report = run_scaling_experiment(load_map(ROOT / "examples/maps/indoor_lab.yaml"), repetitions=2)
    assert [point.node_count for point in report.points] == [1, 2, 3, 4]
    assert all(point.cell_count == 109 for point in report.points)
    assert all(point.repetitions == 2 for point in report.points)
    assert report.points[-1].makespan_distance_m < report.points[0].makespan_distance_m


def test_scaling_rejects_invalid_range() -> None:
    definition = load_map(ROOT / "examples/maps/indoor_lab.yaml")
    with pytest.raises(ValueError, match="node range"):
        run_scaling_experiment(definition, max_nodes=5)
