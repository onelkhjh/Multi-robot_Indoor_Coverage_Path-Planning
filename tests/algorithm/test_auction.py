from pathlib import Path

import pytest

from scopp.algorithm.auction import allocate_conflict_cells
from scopp.algorithm.clustering import CellClusterAssignment, Cluster, ClusteringResult, cluster_map
from scopp.map.grid import discretize_map
from scopp.map.io import load_map

ROOT = Path(__file__).resolve().parents[2]


def test_indoor_map_allocates_every_cell_exactly_once() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    clustered = cluster_map(mapped)
    result = allocate_conflict_cells(mapped, clustered)
    allocated = [cell_id for node in result.nodes for cell_id in node.cell_ids]
    assert len(allocated) == len(mapped.cells)
    assert len(set(allocated)) == len(mapped.cells)
    assert len(result.auction_decisions) == len(clustered.conflict_cell_ids)
    assert result.bias == 0.5


def test_auction_is_deterministic() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    clustered = cluster_map(mapped)
    assert allocate_conflict_cells(mapped, clustered) == allocate_conflict_cells(mapped, clustered)


def test_zero_bias_prefers_lower_current_load() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    base = cluster_map(mapped)
    first, second, conflict = mapped.cells[:3]
    assignments = [
        CellClusterAssignment(first.id, (0,)),
        CellClusterAssignment(second.id, (0,)),
        CellClusterAssignment(conflict.id, (0, 1)),
    ]
    assignments.extend(CellClusterAssignment(cell.id, (1,)) for cell in mapped.cells[3:])
    custom = ClusteringResult(base.clusters, base.sample_points, base.sample_labels, tuple(assignments), 1, True, base.tolerance_m)
    result = allocate_conflict_cells(mapped, custom, bias=0.0)
    assert result.owner_of(conflict.id) == 0


def test_invalid_bias_is_rejected() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    with pytest.raises(ValueError, match="bias"):
        allocate_conflict_cells(mapped, cluster_map(mapped), bias=-0.1)
