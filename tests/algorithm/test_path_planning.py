from pathlib import Path

import pytest

from scopp import allocate_conflict_cells, cluster_map, discretize_map, load_map, plan_coverage_paths
from scopp.algorithm.auction import AllocationResult, NodeAllocation

ROOT = Path(__file__).resolve().parents[2]


def test_paths_visit_every_allocated_cell_once() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    allocation = allocate_conflict_cells(mapped, cluster_map(mapped))
    plan = plan_coverage_paths(mapped, allocation)
    assert len(plan.paths) == 4
    for path, assigned in zip(plan.paths, allocation.nodes):
        assert len(path.cell_ids) == len(set(path.cell_ids))
        assert set(path.cell_ids) == set(assigned.cell_ids)
        assert len(path.waypoints) == len(path.cell_ids)
        assert path.trajectory[0] == path.start
        assert path.trajectory[-1] == path.start
        assert path.distance_m >= 0
    assert plan.makespan_distance_m == max(path.distance_m for path in plan.paths)


def test_nearest_neighbor_starts_at_nearest_cell() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    ids = tuple(cell.id for cell in mapped.cells[:3])
    nodes = tuple(
        NodeAllocation(index, node.id, ids if index == 0 else ())
        for index, node in enumerate(mapped.source.node_starts)
    )
    allocation = AllocationResult(nodes, tuple((cell_id, 0) for cell_id in ids), (), 0.5, (0.0, 0.0, 0.0, 0.0))
    path = plan_coverage_paths(mapped, allocation).paths[0]
    start = mapped.source.node_starts[0].position
    expected = min(mapped.cells[:3], key=lambda cell: ((cell.center[0] - start[0]) ** 2 + (cell.center[1] - start[1]) ** 2, mapped.cells.index(cell)))
    assert path.cell_ids[0] == expected.id


def test_plan_is_deterministic() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    allocation = allocate_conflict_cells(mapped, cluster_map(mapped))
    assert plan_coverage_paths(mapped, allocation) == plan_coverage_paths(mapped, allocation)


def test_total_distance_matches_path_sum() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    plan = plan_coverage_paths(mapped, allocate_conflict_cells(mapped, cluster_map(mapped)))
    assert plan.total_distance_m == pytest.approx(sum(path.distance_m for path in plan.paths))
