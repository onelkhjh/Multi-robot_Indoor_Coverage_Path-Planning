"""Single orchestration entry point for the complete SCoPP pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from scopp.algorithm.auction import AllocationResult, allocate_conflict_cells
from scopp.algorithm.clustering import ClusteringResult, cluster_map
from scopp.algorithm.path_planning import PathPlan, plan_coverage_paths
from scopp.config import ScoppConfig
from scopp.map.grid import discretize_map
from scopp.map.io import load_map
from scopp.map.models import DiscretizedMap, MapDefinition


@dataclass(frozen=True, slots=True)
class PipelineTimings:
    discretization_s: float
    clustering_s: float
    auction_s: float
    path_planning_s: float
    total_s: float


@dataclass(frozen=True, slots=True)
class PipelineResult:
    config: ScoppConfig
    mapped: DiscretizedMap
    clustered: ClusteringResult
    allocation: AllocationResult
    plan: PathPlan
    timings: PipelineTimings


class ScoppPipeline:
    def __init__(self, config: ScoppConfig | None = None) -> None:
        self.config = config or ScoppConfig()

    def run_definition(self, definition: MapDefinition) -> PipelineResult:
        total_start = perf_counter()
        start = perf_counter()
        mapped = discretize_map(definition)
        discretization_s = perf_counter() - start

        start = perf_counter()
        clustered = cluster_map(
            mapped,
            profile=self.config.clustering_profile,
            random_seed=self.config.random_seed,
            tolerance_m=self.config.clustering_tolerance_m,
            max_iterations=self.config.clustering_max_iterations,
        )
        clustering_s = perf_counter() - start

        start = perf_counter()
        allocation = allocate_conflict_cells(mapped, clustered, bias=self.config.auction_bias)
        auction_s = perf_counter() - start

        start = perf_counter()
        plan = plan_coverage_paths(mapped, allocation)
        path_planning_s = perf_counter() - start
        timings = PipelineTimings(discretization_s, clustering_s, auction_s, path_planning_s, perf_counter() - total_start)
        return PipelineResult(self.config, mapped, clustered, allocation, plan, timings)

    def run_map(self, path: str | Path) -> PipelineResult:
        return self.run_definition(load_map(path))


__all__ = ["PipelineResult", "PipelineTimings", "ScoppPipeline"]
