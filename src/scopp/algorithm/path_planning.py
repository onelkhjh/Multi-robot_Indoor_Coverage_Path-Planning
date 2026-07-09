"""Nearest-neighbor coverage paths from SCoPP Section III-E."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import hypot

from scopp.algorithm.auction import AllocationResult
from scopp.config import PathPlanningProfile
from scopp.map.models import DiscretizedMap, XY


@dataclass(frozen=True, slots=True)
class _PointItem:
    point: XY
    stable_index: int
    cell_id: str


@dataclass(frozen=True, slots=True)
class _KDNode:
    item: _PointItem
    axis: int
    left: _KDNode | None
    right: _KDNode | None


def _build(items: tuple[_PointItem, ...], depth: int = 0) -> _KDNode | None:
    if not items:
        return None
    axis = depth % 2
    ordered = tuple(sorted(items, key=lambda item: (item.point[axis], item.point[1 - axis], item.stable_index)))
    middle = len(ordered) // 2
    return _KDNode(ordered[middle], axis, _build(ordered[:middle], depth + 1), _build(ordered[middle + 1 :], depth + 1))


def _nearest(root: _KDNode, target: XY) -> _PointItem:
    best_item = root.item
    best_key = ((root.item.point[0] - target[0]) ** 2 + (root.item.point[1] - target[1]) ** 2, root.item.stable_index)

    def visit(node: _KDNode | None) -> None:
        nonlocal best_item, best_key
        if node is None:
            return
        distance = (node.item.point[0] - target[0]) ** 2 + (node.item.point[1] - target[1]) ** 2
        key = (distance, node.item.stable_index)
        if key < best_key:
            best_item, best_key = node.item, key
        delta = target[node.axis] - node.item.point[node.axis]
        near, far = (node.left, node.right) if delta <= 0 else (node.right, node.left)
        visit(near)
        if delta * delta <= best_key[0]:
            visit(far)

    visit(root)
    return best_item


@dataclass(frozen=True, slots=True)
class NodePath:
    cluster_index: int
    node_id: str
    start: XY
    cell_ids: tuple[str, ...]
    waypoints: tuple[XY, ...]
    motion_cell_ids: tuple[str, ...]
    motion_waypoints: tuple[XY, ...]
    return_motion_index: int
    distance_m: float

    @property
    def trajectory(self) -> tuple[XY, ...]:
        """Official-code trajectory: start, all cell centres, then return."""
        return (self.start,) + self.motion_waypoints + ((self.start,) if self.motion_waypoints else ())


@dataclass(frozen=True, slots=True)
class PathPlan:
    paths: tuple[NodePath, ...]

    @property
    def makespan_distance_m(self) -> float:
        """Return the longest node path, the paper objective at equal speed."""
        return max((path.distance_m for path in self.paths), default=0.0)

    @property
    def total_distance_m(self) -> float:
        return sum(path.distance_m for path in self.paths)


def _ordered_nearest_neighbor(start: XY, items: tuple[_PointItem, ...]) -> tuple[_PointItem, ...]:
    remaining = items
    current = start
    route: list[_PointItem] = []
    while remaining:
        tree = _build(remaining)
        assert tree is not None
        chosen = _nearest(tree, current)
        route.append(chosen)
        current = chosen.point
        remaining = tuple(item for item in remaining if item.cell_id != chosen.cell_id)
    return tuple(route)


class NoAdjacentPathError(ValueError):
    """Raised when two coverage targets cannot be connected by valid cells."""


class MetricTspTooLargeError(ValueError):
    """Raised when exact metric-closure TSP would be impractically large."""


def _adjacent_path(start_id: str, goal_id: str, cells_by_id, ids_by_key) -> tuple[str, ...]:
    """Return a deterministic 4-neighbor A* path including both endpoints."""
    if start_id == goal_id:
        return (start_id,)
    start, goal = cells_by_id[start_id], cells_by_id[goal_id]
    start_key, goal_key = (start.row, start.col), (goal.row, goal.col)
    frontier: list[tuple[int, int, int, tuple[int, int]]] = []
    heappush(frontier, (0, 0, 0, start_key))
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start_key: None}
    cost = {start_key: 0}
    sequence = 0
    neighbor_offsets = ((-1, 0), (0, -1), (0, 1), (1, 0))
    while frontier:
        _, current_cost, _, current = heappop(frontier)
        if current == goal_key:
            keys: list[tuple[int, int]] = []
            cursor: tuple[int, int] | None = current
            while cursor is not None:
                keys.append(cursor)
                cursor = came_from[cursor]
            return tuple(ids_by_key[key] for key in reversed(keys))
        if current_cost != cost[current]:
            continue
        for dr, dc in neighbor_offsets:
            neighbor = (current[0] + dr, current[1] + dc)
            if neighbor not in ids_by_key:
                continue
            new_cost = current_cost + 1
            if new_cost < cost.get(neighbor, 10**18):
                cost[neighbor] = new_cost
                came_from[neighbor] = current
                sequence += 1
                heuristic = abs(neighbor[0] - goal_key[0]) + abs(neighbor[1] - goal_key[1])
                heappush(frontier, (new_cost + heuristic, new_cost, sequence, neighbor))
    raise NoAdjacentPathError(f"no valid 4-neighbor path between {start_id!r} and {goal_id!r}")


def _start_cell_id(mapped: DiscretizedMap, start: XY, stable_index: dict[str, int]) -> str:
    return min(
        mapped.cells,
        key=lambda cell: ((cell.center[0] - start[0]) ** 2 + (cell.center[1] - start[1]) ** 2, stable_index[cell.id]),
    ).id


def _shortest_cell_path(start_id: str, goal_id: str, cells_by_id, ids_by_key) -> tuple[str, ...]:
    return _adjacent_path(start_id, goal_id, cells_by_id, ids_by_key)


def _metric_distance_matrix(node_ids: tuple[str, ...], cells_by_id, ids_by_key, cell_width: float) -> tuple[tuple[float, ...], ...]:
    matrix: list[tuple[float, ...]] = []
    for source in node_ids:
        row: list[float] = []
        for target in node_ids:
            if source == target:
                row.append(0.0)
            else:
                row.append((len(_shortest_cell_path(source, target, cells_by_id, ids_by_key)) - 1) * cell_width)
        matrix.append(tuple(row))
    return tuple(matrix)


def _held_karp_cycle_order(distance: tuple[tuple[float, ...], ...], *, max_targets: int = 20) -> tuple[int, ...]:
    """Return target indices in a shortest cycle from depot 0 back to depot 0.

    The metric closure encodes graph shortest-path distances. Exact Held-Karp is
    exponential, so large instances should use the paper NN profile or a future
    MILP/OR-Tools backend.
    """
    target_count = len(distance) - 1
    if target_count <= 0:
        return ()
    if target_count > max_targets:
        raise MetricTspTooLargeError(
            f"metric_tsp exact solver supports at most {max_targets} targets, got {target_count}"
        )
    states: dict[tuple[int, int], tuple[float, int]] = {}
    for target in range(1, len(distance)):
        mask = 1 << (target - 1)
        states[(mask, target)] = (distance[0][target], 0)
    full_mask = (1 << target_count) - 1
    for mask in range(1, full_mask + 1):
        for last in range(1, len(distance)):
            key = (mask, last)
            if key not in states:
                continue
            for nxt in range(1, len(distance)):
                bit = 1 << (nxt - 1)
                if mask & bit:
                    continue
                next_mask = mask | bit
                candidate_cost = states[key][0] + distance[last][nxt]
                candidate = (candidate_cost, last)
                next_key = (next_mask, nxt)
                if next_key not in states or candidate < states[next_key]:
                    states[next_key] = candidate
    best_last = min(
        range(1, len(distance)),
        key=lambda last: (states[(full_mask, last)][0] + distance[last][0], last),
    )
    order: list[int] = []
    mask = full_mask
    last = best_last
    while last:
        order.append(last)
        cost, previous = states[(mask, last)]
        del cost
        mask &= ~(1 << (last - 1))
        last = previous
    return tuple(reversed(order))


def _cycle_cost(distance: tuple[tuple[float, ...], ...], order: tuple[int, ...]) -> float:
    if not order:
        return 0.0
    return distance[0][order[0]] + sum(distance[a][b] for a, b in zip(order, order[1:])) + distance[order[-1]][0]


def _insertion_two_opt_cycle_order(distance: tuple[tuple[float, ...], ...]) -> tuple[int, ...]:
    """Return a deterministic metric-closure TSP heuristic for larger routes."""
    remaining = set(range(1, len(distance)))
    if not remaining:
        return ()
    first = min(remaining, key=lambda item: (distance[0][item], item))
    order = [first]
    remaining.remove(first)
    while remaining:
        best: tuple[float, int, int] | None = None
        for item in remaining:
            for position in range(len(order) + 1):
                previous_node = 0 if position == 0 else order[position - 1]
                next_node = 0 if position == len(order) else order[position]
                increase = distance[previous_node][item] + distance[item][next_node] - distance[previous_node][next_node]
                candidate = (increase, item, position)
                if best is None or candidate < best:
                    best = candidate
        assert best is not None
        _, item, position = best
        order.insert(position, item)
        remaining.remove(item)

    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                before = 0 if i == 0 else order[i - 1]
                first_i = order[i]
                last_j = order[j]
                after = 0 if j == len(order) - 1 else order[j + 1]
                delta = distance[before][last_j] + distance[first_i][after] - distance[before][first_i] - distance[last_j][after]
                if delta < -1e-9:
                    order[i : j + 1] = reversed(order[i : j + 1])
                    improved = True
                    break
            if improved:
                break
    return tuple(order)


def _metric_tsp_order(distance: tuple[tuple[float, ...], ...]) -> tuple[int, ...]:
    try:
        return _held_karp_cycle_order(distance)
    except MetricTspTooLargeError:
        return _insertion_two_opt_cycle_order(distance)


def _plan_paper_nn_paths(mapped: DiscretizedMap, allocation: AllocationResult) -> PathPlan:
    """Order each node's assigned cell centres using KD-tree nearest neighbor."""
    cell_by_id = {cell.id: cell for cell in mapped.cells}
    id_by_key = {(cell.row, cell.col): cell.id for cell in mapped.cells}
    stable_index = {cell.id: index for index, cell in enumerate(mapped.cells)}
    paths: list[NodePath] = []
    node_by_id = {node.id: node for node in mapped.source.node_starts}
    for allocated in allocation.nodes:
        try:
            node = node_by_id[allocated.node_id]
        except KeyError as exc:
            raise ValueError(f"allocation contains unknown node {allocated.node_id!r}") from exc
        items = tuple(_PointItem(cell_by_id[cell_id].center, stable_index[cell_id], cell_id) for cell_id in allocated.cell_ids)
        ordered = _ordered_nearest_neighbor(node.position, items)
        waypoints = tuple(item.point for item in ordered)
        if not ordered:
            paths.append(NodePath(allocated.cluster_index, node.id, node.position, (), (), (), (), 0, 0.0))
            continue
        start_cell = cell_by_id[_start_cell_id(mapped, node.position, stable_index)]
        motion_ids: list[str] = [start_cell.id]
        current_id = start_cell.id
        for target in ordered:
            segment = _adjacent_path(current_id, target.cell_id, cell_by_id, id_by_key)
            motion_ids.extend(segment[1:])
            current_id = target.cell_id
        return_motion_index = len(motion_ids)
        motion_ids.extend(_adjacent_path(current_id, start_cell.id, cell_by_id, id_by_key)[1:])
        motion_waypoints = tuple(cell_by_id[cell_id].center for cell_id in motion_ids)
        distance = hypot(motion_waypoints[0][0] - node.position[0], motion_waypoints[0][1] - node.position[1])
        distance += sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(motion_waypoints, motion_waypoints[1:]))
        distance += hypot(node.position[0] - motion_waypoints[-1][0], node.position[1] - motion_waypoints[-1][1])
        paths.append(NodePath(allocated.cluster_index, node.id, node.position, tuple(item.cell_id for item in ordered), waypoints, tuple(motion_ids), motion_waypoints, return_motion_index, distance))
    return PathPlan(tuple(paths))


def _plan_metric_tsp_paths(mapped: DiscretizedMap, allocation: AllocationResult) -> PathPlan:
    """Use metric-closure TSP over the valid-cell graph for each node route.

    Assignments with at most 20 targets use exact Held-Karp DP. Larger
    assignments use deterministic insertion plus 2-opt on the same metric
    closure so the UI and experiments remain tractable without an external
    solver.
    """
    cell_by_id = {cell.id: cell for cell in mapped.cells}
    id_by_key = {(cell.row, cell.col): cell.id for cell in mapped.cells}
    stable_index = {cell.id: index for index, cell in enumerate(mapped.cells)}
    paths: list[NodePath] = []
    node_by_id = {node.id: node for node in mapped.source.node_starts}
    for allocated in allocation.nodes:
        try:
            node = node_by_id[allocated.node_id]
        except KeyError as exc:
            raise ValueError(f"allocation contains unknown node {allocated.node_id!r}") from exc
        if not allocated.cell_ids:
            paths.append(NodePath(allocated.cluster_index, node.id, node.position, (), (), (), (), 0, 0.0))
            continue
        depot_id = _start_cell_id(mapped, node.position, stable_index)
        required = tuple(sorted(allocated.cell_ids, key=lambda cell_id: stable_index[cell_id]))
        metric_nodes = (depot_id,) + required
        distance_matrix = _metric_distance_matrix(metric_nodes, cell_by_id, id_by_key, mapped.cell_width_m)
        order_indices = _metric_tsp_order(distance_matrix)
        ordered_ids = tuple(metric_nodes[index] for index in order_indices)
        waypoints = tuple(cell_by_id[cell_id].center for cell_id in ordered_ids)
        motion_ids: list[str] = [depot_id]
        current_id = depot_id
        for target_id in ordered_ids:
            segment = _shortest_cell_path(current_id, target_id, cell_by_id, id_by_key)
            motion_ids.extend(segment[1:])
            current_id = target_id
        return_motion_index = len(motion_ids)
        motion_ids.extend(_shortest_cell_path(current_id, depot_id, cell_by_id, id_by_key)[1:])
        motion_waypoints = tuple(cell_by_id[cell_id].center for cell_id in motion_ids)
        distance = hypot(motion_waypoints[0][0] - node.position[0], motion_waypoints[0][1] - node.position[1])
        distance += sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(motion_waypoints, motion_waypoints[1:]))
        distance += hypot(node.position[0] - motion_waypoints[-1][0], node.position[1] - motion_waypoints[-1][1])
        paths.append(NodePath(allocated.cluster_index, node.id, node.position, ordered_ids, waypoints, tuple(motion_ids), motion_waypoints, return_motion_index, distance))
    return PathPlan(tuple(paths))


def plan_coverage_paths(
    mapped: DiscretizedMap,
    allocation: AllocationResult,
    *,
    profile: PathPlanningProfile | str = PathPlanningProfile.PAPER_NN,
) -> PathPlan:
    """Plan per-node coverage routes with the selected path planning profile."""
    if len(allocation.nodes) != len(mapped.source.node_starts):
        raise ValueError("allocation node count does not match map node count")
    selected = PathPlanningProfile(profile)
    if selected is PathPlanningProfile.PAPER_NN:
        return _plan_paper_nn_paths(mapped, allocation)
    if selected is PathPlanningProfile.METRIC_TSP:
        return _plan_metric_tsp_paths(mapped, allocation)
    raise ValueError(f"unsupported path planning profile {profile!r}")


__all__ = ["MetricTspTooLargeError", "NoAdjacentPathError", "NodePath", "PathPlan", "plan_coverage_paths"]
