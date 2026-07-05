from pathlib import Path

import pytest

from scopp.experiment import run_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_indoor_experiment_report_contains_paper_metrics() -> None:
    report = run_experiment(ROOT / "examples/maps/indoor_lab.yaml")
    assert report.cell_count == 109
    assert report.node_count == 4
    assert report.conflict_cell_count == 15
    assert report.cell_count_range == 2
    assert report.makespan_distance_m == pytest.approx(max(node.distance_m for node in report.node_metrics))
    assert report.total_distance_m == pytest.approx(sum(node.distance_m for node in report.node_metrics))
    assert report.clustering_iterations <= 10
    assert report.clustering_converged
    assert report.boundary_policy == "any_overlap"


def test_algorithm_metrics_repeat_while_timings_may_vary() -> None:
    first = run_experiment(ROOT / "examples/maps/indoor_lab.yaml")
    second = run_experiment(ROOT / "examples/maps/indoor_lab.yaml")
    assert first.node_metrics == second.node_metrics
    assert first.makespan_distance_m == second.makespan_distance_m
    assert first.cell_count_cv == second.cell_count_cv
    assert first.timings.total_s >= 0
