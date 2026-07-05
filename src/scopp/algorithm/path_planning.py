"""Nearest-neighbor coverage paths from SCoPP Section III-E."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from scopp.algorithm.auction import AllocationResult
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
    distance_m: float

    @property
    def trajectory(self) -> tuple[XY, ...]:
        """Official-code trajectory: start, all cell centres, then return."""
        return (self.start,) + self.waypoints + ((self.start,) if self.waypoints else ())


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


def plan_coverage_paths(mapped: DiscretizedMap, allocation: AllocationResult) -> PathPlan:
    """Order each node's assigned cell centres using KD-tree nearest neighbor."""
    if len(allocation.nodes) != len(mapped.source.node_starts):
        raise ValueError("allocation node count does not match map node count")
    cell_by_id = {cell.id: cell for cell in mapped.cells}
    stable_index = {cell.id: index for index, cell in enumerate(mapped.cells)}
    paths: list[NodePath] = []
    for allocated, node in zip(allocation.nodes, mapped.source.node_starts):
        if allocated.node_id != node.id:
            raise ValueError("allocation node order does not match map node order")
        items = tuple(_PointItem(cell_by_id[cell_id].center, stable_index[cell_id], cell_id) for cell_id in allocated.cell_ids)
        ordered = _ordered_nearest_neighbor(node.position, items)
        waypoints = tuple(item.point for item in ordered)
        distance = 0.0
        previous = node.position
        for waypoint in waypoints:
            distance += hypot(waypoint[0] - previous[0], waypoint[1] - previous[1])
            previous = waypoint
        if waypoints:
            distance += hypot(node.position[0] - previous[0], node.position[1] - previous[1])
        paths.append(NodePath(allocated.cluster_index, node.id, node.position, tuple(item.cell_id for item in ordered), waypoints, distance))
    return PathPlan(tuple(paths))
