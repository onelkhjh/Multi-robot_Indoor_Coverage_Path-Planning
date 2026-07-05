"""Lloyd clustering stage from SCoPP Section III-C."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from scopp.map.models import DiscretizedMap, XY


@dataclass(frozen=True, slots=True)
class Cluster:
    index: int
    node_id: str
    centroid: XY
    sample_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CellClusterAssignment:
    cell_id: str
    cluster_indices: tuple[int, ...]

    @property
    def is_conflict(self) -> bool:
        return len(self.cluster_indices) > 1


@dataclass(frozen=True, slots=True)
class ClusteringResult:
    clusters: tuple[Cluster, ...]
    sample_points: tuple[XY, ...]
    sample_labels: tuple[int, ...]
    cell_assignments: tuple[CellClusterAssignment, ...]
    iterations: int
    converged: bool
    tolerance_m: float

    @property
    def conflict_cell_ids(self) -> tuple[str, ...]:
        return tuple(item.cell_id for item in self.cell_assignments if item.is_conflict)


def _nearest(point: XY, centroids: tuple[XY, ...]) -> int:
    """Return nearest centroid; lower stable node index wins exact ties."""
    return min(range(len(centroids)), key=lambda index: ((point[0] - centroids[index][0]) ** 2 + (point[1] - centroids[index][1]) ** 2, index))


def lloyd_cluster(
    points: tuple[XY, ...],
    initial_centroids: tuple[XY, ...],
    *,
    tolerance_m: float,
    max_iterations: int = 10,
) -> tuple[tuple[XY, ...], tuple[int, ...], int, bool]:
    """Cluster perimeter samples using the paper's bounded Lloyd iteration.

    Empty clusters retain their previous centroid. This explicit policy avoids
    hidden randomness and keeps a node represented when a small map is used.
    """
    if not points:
        raise ValueError("at least one perimeter sample is required")
    if not initial_centroids:
        raise ValueError("at least one node centroid is required")
    if tolerance_m <= 0:
        raise ValueError("tolerance_m must be greater than zero")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be greater than zero")

    centroids = initial_centroids
    labels: tuple[int, ...] = ()
    for iteration in range(1, max_iterations + 1):
        labels = tuple(_nearest(point, centroids) for point in points)
        updated: list[XY] = []
        for index, old in enumerate(centroids):
            members = tuple(point for point, label in zip(points, labels) if label == index)
            if members:
                updated.append((sum(p[0] for p in members) / len(members), sum(p[1] for p in members) / len(members)))
            else:
                updated.append(old)
        next_centroids = tuple(updated)
        movement = max(hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(centroids, next_centroids))
        centroids = next_centroids
        if movement <= tolerance_m:
            final_labels = tuple(_nearest(point, centroids) for point in points)
            return centroids, final_labels, iteration, True
    return centroids, tuple(_nearest(point, centroids) for point in points), max_iterations, False


def cluster_map(
    value: DiscretizedMap,
    *,
    tolerance_m: float | None = None,
    max_iterations: int = 10,
) -> ClusteringResult:
    """Cluster all cell perimeter samples and identify conflict cells.

    The default tolerance is the paper setting ``W/8``. Initial centroids are
    node starting positions in their stable map-file order.
    """
    if not value.source.node_starts:
        raise ValueError("SCoPP clustering requires at least one node")
    points = tuple(point for cell in value.cells for point in cell.perimeter_samples)
    initial = tuple(node.position for node in value.source.node_starts)
    tolerance = tolerance_m if tolerance_m is not None else value.cell_width_m / 8.0
    centroids, labels, iterations, converged = lloyd_cluster(
        points, initial, tolerance_m=tolerance, max_iterations=max_iterations
    )
    clusters = tuple(
        Cluster(index, value.source.node_starts[index].id, centroid, tuple(i for i, label in enumerate(labels) if label == index))
        for index, centroid in enumerate(centroids)
    )
    assignments: list[CellClusterAssignment] = []
    offset = 0
    for cell in value.cells:
        count = len(cell.perimeter_samples)
        assignments.append(CellClusterAssignment(cell.id, tuple(sorted(set(labels[offset:offset + count])))))
        offset += count
    return ClusteringResult(clusters, points, labels, tuple(assignments), iterations, converged, tolerance)
