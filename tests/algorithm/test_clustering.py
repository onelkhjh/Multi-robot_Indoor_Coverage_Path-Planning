from pathlib import Path

import pytest

from scopp.algorithm.clustering import cluster_map, lloyd_cluster
from scopp.map.grid import discretize_map
from scopp.map.io import load_map

ROOT = Path(__file__).resolve().parents[2]


def test_lloyd_separates_two_groups_deterministically() -> None:
    points = ((0.0, 0.0), (0.0, 2.0), (10.0, 0.0), (10.0, 2.0))
    result = lloyd_cluster(points, ((0.0, 1.0), (10.0, 1.0)), tolerance_m=0.1)
    centroids, labels, iterations, converged = result
    assert centroids == ((0.0, 1.0), (10.0, 1.0))
    assert labels == (0, 0, 1, 1)
    assert iterations == 1
    assert converged


def test_exact_tie_uses_lower_node_index() -> None:
    _, labels, _, _ = lloyd_cluster(((5.0, 0.0),), ((0.0, 0.0), (10.0, 0.0)), tolerance_m=0.1)
    assert labels == (0,)


def test_indoor_map_uses_paper_iteration_defaults() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    result = cluster_map(mapped)
    assert len(result.clusters) == 4
    assert result.iterations <= 10
    assert result.tolerance_m == pytest.approx(mapped.cell_width_m / 8)
    assert len(result.cell_assignments) == len(mapped.cells)
    assert result.conflict_cell_ids


def test_clustering_repeats_exactly() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    assert cluster_map(mapped) == cluster_map(mapped)
