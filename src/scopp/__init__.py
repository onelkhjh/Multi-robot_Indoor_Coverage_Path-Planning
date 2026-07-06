"""SCoPP paper reproduction package."""

from .map.footprint import coverage_width
from .map.grid import discretize_map
from .map.io import load_map
from .algorithm.clustering import cluster_map
from .algorithm.auction import allocate_conflict_cells
from .algorithm.path_planning import plan_coverage_paths
from .experiment import run_experiment
from .config import ClusteringProfile, ScoppConfig
from .pipeline import PipelineResult, ScoppPipeline

__all__ = ["ClusteringProfile", "PipelineResult", "ScoppConfig", "ScoppPipeline", "allocate_conflict_cells", "cluster_map", "coverage_width", "discretize_map", "load_map", "plan_coverage_paths", "run_experiment"]
