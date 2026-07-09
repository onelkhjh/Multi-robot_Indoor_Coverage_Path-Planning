import pytest

from scopp.config import ClusteringProfile, PathPlanningProfile, ScoppConfig


def test_config_parses_cli_profile() -> None:
    value = ScoppConfig.from_cli("official_minibatch", 17, 0.25, "metric_tsp")
    assert value.clustering_profile is ClusteringProfile.OFFICIAL_MINIBATCH
    assert value.path_planning_profile is PathPlanningProfile.METRIC_TSP
    assert value.random_seed == 17
    assert value.auction_bias == 0.25


@pytest.mark.parametrize(
    "kwargs",
    [
        {"auction_bias": -1},
        {"clustering_tolerance_m": 0},
        {"clustering_max_iterations": 0},
    ],
)
def test_config_rejects_invalid_values(kwargs) -> None:
    with pytest.raises(ValueError):
        ScoppConfig(**kwargs)
