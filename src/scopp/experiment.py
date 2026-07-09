"""Reproducible execution and metrics for SCoPP experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, pstdev
from scopp.map.io import load_map
from scopp.map.models import MapDefinition
from scopp.config import ClusteringProfile, ScoppConfig
from scopp.pipeline import ScoppPipeline


@dataclass(frozen=True, slots=True)
class NodeMetrics:
    node_id: str
    cell_count: int
    distance_m: float


@dataclass(frozen=True, slots=True)
class StageTimings:
    discretization_s: float
    clustering_s: float
    auction_s: float
    path_planning_s: float
    total_s: float


@dataclass(frozen=True, slots=True)
class ExperimentReport:
    schema_version: str
    map_name: str
    map_path: str
    boundary_policy: str
    cell_width_m: float
    cell_count: int
    node_count: int
    conflict_cell_count: int
    clustering_iterations: int
    clustering_converged: bool
    clustering_profile: str
    path_planning_profile: str
    random_seed: int | None
    auction_bias: float
    node_metrics: tuple[NodeMetrics, ...]
    cell_count_range: int
    cell_count_cv: float
    distance_range_m: float
    distance_cv: float
    makespan_distance_m: float
    total_distance_m: float
    timings: StageTimings

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _coefficient_of_variation(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    mean = fmean(values)
    return pstdev(values) / mean if mean else 0.0


def run_definition(
    definition: MapDefinition,
    *,
    map_path: str = "<in-memory>",
    auction_bias: float = 0.5,
    clustering_profile: str = "deterministic_lloyd",
    random_seed: int = 0,
    config: ScoppConfig | None = None,
) -> ExperimentReport:
    """Execute the complete pipeline for an already validated map."""
    settings = config or ScoppConfig(
        clustering_profile=ClusteringProfile(clustering_profile),
        random_seed=random_seed,
        auction_bias=auction_bias,
    )
    pipeline = ScoppPipeline(settings).run_definition(definition)
    mapped, clustered, allocated, planned = pipeline.mapped, pipeline.clustered, pipeline.allocation, pipeline.plan

    node_metrics = tuple(
        NodeMetrics(path.node_id, len(path.cell_ids), path.distance_m)
        for path in planned.paths
    )
    counts = tuple(float(item.cell_count) for item in node_metrics)
    distances = tuple(item.distance_m for item in node_metrics)
    return ExperimentReport(
        schema_version="1.0",
        map_name=definition.name,
        map_path=map_path,
        boundary_policy=definition.grid.boundary_policy.value,
        cell_width_m=mapped.cell_width_m,
        cell_count=len(mapped.cells),
        node_count=len(definition.node_starts),
        conflict_cell_count=len(allocated.auction_decisions),
        clustering_iterations=clustered.iterations,
        clustering_converged=clustered.converged,
        clustering_profile=clustered.profile,
        path_planning_profile=settings.path_planning_profile.value,
        random_seed=clustered.random_seed,
        auction_bias=settings.auction_bias,
        node_metrics=node_metrics,
        cell_count_range=int(max(counts) - min(counts)) if counts else 0,
        cell_count_cv=_coefficient_of_variation(counts),
        distance_range_m=max(distances) - min(distances) if distances else 0.0,
        distance_cv=_coefficient_of_variation(distances),
        makespan_distance_m=planned.makespan_distance_m,
        total_distance_m=planned.total_distance_m,
        timings=StageTimings(
            pipeline.timings.discretization_s,
            pipeline.timings.clustering_s,
            pipeline.timings.auction_s,
            pipeline.timings.path_planning_s,
            pipeline.timings.total_s,
        ),
    )


def run_experiment(
    map_path: str | Path,
    *,
    auction_bias: float = 0.5,
    clustering_profile: str = "deterministic_lloyd",
    random_seed: int = 0,
    config: ScoppConfig | None = None,
) -> ExperimentReport:
    """Load a map, execute the complete SCoPP pipeline, and collect metrics."""
    source_path = Path(map_path)
    return run_definition(load_map(source_path), map_path=source_path.as_posix(), auction_bias=auction_bias, clustering_profile=clustering_profile, random_seed=random_seed, config=config)
