"""Node-count scaling experiments corresponding to the SCoPP evaluation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import fmean, pstdev

from scopp.experiment import ExperimentReport, run_definition
from scopp.map.models import MapDefinition


@dataclass(frozen=True, slots=True)
class ScalingPoint:
    node_count: int
    repetitions: int
    cell_count: int
    conflict_cell_count: int
    cell_count_range: int
    cell_count_cv: float
    makespan_distance_m: float
    total_distance_m: float
    mean_runtime_s: float
    runtime_std_s: float


@dataclass(frozen=True, slots=True)
class ScalingReport:
    map_name: str
    points: tuple[ScalingPoint, ...]


def run_scaling_experiment(
    definition: MapDefinition,
    *,
    min_nodes: int = 1,
    max_nodes: int | None = None,
    repetitions: int = 3,
    auction_bias: float = 0.5,
) -> ScalingReport:
    """Evaluate deterministic outputs and runtime as the node count increases."""
    available = len(definition.node_starts)
    upper = available if max_nodes is None else max_nodes
    if not 1 <= min_nodes <= upper <= available:
        raise ValueError("node range must be within the map's available node starts")
    if repetitions <= 0:
        raise ValueError("repetitions must be greater than zero")
    points: list[ScalingPoint] = []
    for node_count in range(min_nodes, upper + 1):
        variant = replace(definition, node_starts=definition.node_starts[:node_count])
        runs = tuple(run_definition(variant, auction_bias=auction_bias) for _ in range(repetitions))
        baseline: ExperimentReport = runs[0]
        signature = (baseline.node_metrics, baseline.conflict_cell_count, baseline.makespan_distance_m)
        if any((run.node_metrics, run.conflict_cell_count, run.makespan_distance_m) != signature for run in runs[1:]):
            raise RuntimeError("algorithm output changed across identical repetitions")
        runtimes = tuple(run.timings.total_s for run in runs)
        points.append(ScalingPoint(
            node_count, repetitions, baseline.cell_count, baseline.conflict_cell_count,
            baseline.cell_count_range, baseline.cell_count_cv,
            baseline.makespan_distance_m, baseline.total_distance_m,
            fmean(runtimes), pstdev(runtimes),
        ))
    return ScalingReport(definition.name, tuple(points))
