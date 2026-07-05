"""Conflict-cell allocation from SCoPP Section III-D."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

from scopp.algorithm.clustering import ClusteringResult
from scopp.map.models import DiscretizedMap, XY


@dataclass(frozen=True, slots=True)
class AuctionDecision:
    cell_id: str
    candidates: tuple[int, ...]
    bids: tuple[float, ...]
    winner: int


@dataclass(frozen=True, slots=True)
class NodeAllocation:
    cluster_index: int
    node_id: str
    cell_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AllocationResult:
    nodes: tuple[NodeAllocation, ...]
    owner_by_cell: tuple[tuple[str, int], ...]
    auction_decisions: tuple[AuctionDecision, ...]
    bias: float
    distance_biases: tuple[float, ...]

    def owner_of(self, cell_id: str) -> int:
        for candidate_id, owner in self.owner_by_cell:
            if candidate_id == cell_id:
                return owner
        raise KeyError(cell_id)


def _distance_to_region(start: XY, centers: tuple[XY, ...]) -> float:
    """Return distance from a start to its nearest initially dominated cell."""
    return min(hypot(start[0] - center[0], start[1] - center[1]) for center in centers)


def allocate_conflict_cells(
    mapped: DiscretizedMap,
    clustered: ClusteringResult,
    *,
    bias: float = 0.5,
) -> AllocationResult:
    """Assign all cells using the SCoPP greedy conflict auction.

    Non-conflict cells retain their sole Lloyd cluster. Conflict cells are
    processed in stable map order. For candidate robot ``r`` the bid is
    ``N_r + B * d0(r)`` where official code fixes ``d0`` before the auction as
    the rounded number of cell widths from the robot start to its nearest
    initially dominated cell. Lower cluster index wins exact bid ties.
    """
    if not isfinite(bias) or bias < 0:
        raise ValueError("bias must be finite and non-negative")
    if len(clustered.cell_assignments) != len(mapped.cells):
        raise ValueError("clustering result does not match the discretized map")
    if len(clustered.clusters) != len(mapped.source.node_starts):
        raise ValueError("cluster count does not match node count")

    cell_by_id = {cell.id: cell for cell in mapped.cells}
    assigned: list[list[str]] = [[] for _ in clustered.clusters]
    owners: dict[str, int] = {}
    conflicts = []
    for assignment in clustered.cell_assignments:
        if not assignment.cluster_indices:
            raise ValueError(f"cell {assignment.cell_id!r} has no cluster candidate")
        if assignment.is_conflict:
            conflicts.append(assignment)
        else:
            owner = assignment.cluster_indices[0]
            assigned[owner].append(assignment.cell_id)
            owners[assignment.cell_id] = owner

    decisions: list[AuctionDecision] = []
    starts = tuple(node.position for node in mapped.source.node_starts)
    distance_biases: list[float] = []
    for cluster_index, start in enumerate(starts):
        initial_centers = tuple(cell_by_id[cell_id].center for cell_id in assigned[cluster_index])
        if not initial_centers:
            candidate_centers = tuple(
                cell_by_id[item.cell_id].center
                for item in clustered.cell_assignments
                if cluster_index in item.cluster_indices
            )
            if not candidate_centers:
                distance_biases.append(0.0)
                continue
            initial_centers = candidate_centers
        distance_in_cells = round(_distance_to_region(start, initial_centers) / mapped.cell_width_m)
        distance_biases.append(distance_in_cells * bias)
    for assignment in conflicts:
        cell = cell_by_id[assignment.cell_id]
        bids: list[float] = []
        for candidate in assignment.cluster_indices:
            bids.append(len(assigned[candidate]) + distance_biases[candidate])
        winner_offset = min(range(len(bids)), key=lambda index: (bids[index], assignment.cluster_indices[index]))
        winner = assignment.cluster_indices[winner_offset]
        assigned[winner].append(assignment.cell_id)
        owners[assignment.cell_id] = winner
        decisions.append(AuctionDecision(assignment.cell_id, assignment.cluster_indices, tuple(bids), winner))

    node_results = tuple(
        NodeAllocation(index, node.id, tuple(assigned[index]))
        for index, node in enumerate(mapped.source.node_starts)
    )
    owner_by_cell = tuple((cell.id, owners[cell.id]) for cell in mapped.cells)
    return AllocationResult(node_results, owner_by_cell, tuple(decisions), bias, tuple(distance_biases))
