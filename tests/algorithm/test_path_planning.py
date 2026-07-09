from pathlib import Path

import pytest

from scopp import PathPlanningProfile, allocate_conflict_cells, cluster_map, discretize_map, load_map, plan_coverage_paths
from scopp.algorithm.auction import AllocationResult, NodeAllocation
from scopp.map.schema import parse_map

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
        assert len(path.motion_cell_ids) == len(path.motion_waypoints)
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


def test_motion_path_uses_only_four_neighbor_cells() -> None:
    mapped = discretize_map(load_map(ROOT / "examples/maps/indoor_lab.yaml"))
    plan = plan_coverage_paths(mapped, allocate_conflict_cells(mapped, cluster_map(mapped)))
    by_id = {cell.id: cell for cell in mapped.cells}
    for path in plan.paths:
        for first, second in zip(path.motion_cell_ids, path.motion_cell_ids[1:]):
            a, b = by_id[first], by_id[second]
            assert abs(a.row - b.row) + abs(a.col - b.col) == 1


def test_metric_tsp_uses_shortest_metric_closure_cycle() -> None:
    mapped = discretize_map(parse_map({
        "schema_version": "1.0",
        "name": "metric-tsp",
        "coordinates": {"kind": "cartesian", "unit": "m"},
        "aoi": {"exterior": [[0, 0], [3, 0], [3, 4], [0, 4]]},
        "nodes": [{"id": "n1", "position": [0.5, 0.5]}],
        "sensor": {"altitude_m": 0.5, "fov_deg": 90},
        "grid": {"origin": [0, 0], "boundary_policy": "paper_center"},
    }))
    ids = ("r1_c0", "r2_c0", "r3_c0", "r0_c1", "r1_c2")
    allocation = AllocationResult((NodeAllocation(0, "n1", ids),), tuple((cell_id, 0) for cell_id in ids), (), 0.5, (0.0,))

    greedy = plan_coverage_paths(mapped, allocation, profile=PathPlanningProfile.PAPER_NN).paths[0]
    optimal = plan_coverage_paths(mapped, allocation, profile=PathPlanningProfile.METRIC_TSP).paths[0]

    assert greedy.distance_m == pytest.approx(12.0)
    assert optimal.distance_m == pytest.approx(10.0)
    assert set(optimal.cell_ids) == set(ids)
