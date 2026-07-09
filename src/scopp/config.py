"""Typed configuration shared by SCoPP APIs and command-line tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class ClusteringProfile(str, Enum):
    DETERMINISTIC_LLOYD = "deterministic_lloyd"
    OFFICIAL_MINIBATCH = "official_minibatch"


class PathPlanningProfile(str, Enum):
    PAPER_NN = "paper_nn"
    METRIC_TSP = "metric_tsp"


@dataclass(frozen=True, slots=True)
class ScoppConfig:
    clustering_profile: ClusteringProfile = ClusteringProfile.DETERMINISTIC_LLOYD
    path_planning_profile: PathPlanningProfile = PathPlanningProfile.PAPER_NN
    random_seed: int = 0
    auction_bias: float = 0.5
    clustering_tolerance_m: float | None = None
    clustering_max_iterations: int = 10

    def __post_init__(self) -> None:
        if not isfinite(self.auction_bias) or self.auction_bias < 0:
            raise ValueError("auction_bias must be finite and non-negative")
        if self.clustering_tolerance_m is not None and (
            not isfinite(self.clustering_tolerance_m) or self.clustering_tolerance_m <= 0
        ):
            raise ValueError("clustering_tolerance_m must be finite and greater than zero")
        if self.clustering_max_iterations <= 0:
            raise ValueError("clustering_max_iterations must be greater than zero")

    @classmethod
    def from_cli(cls, profile: str, seed: int, bias: float = 0.5, path_profile: str = PathPlanningProfile.PAPER_NN.value) -> "ScoppConfig":
        return cls(ClusteringProfile(profile), PathPlanningProfile(path_profile), seed, bias)
