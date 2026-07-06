from pathlib import Path

from scopp import ClusteringProfile, ScoppConfig, ScoppPipeline

ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_runs_every_stage_from_one_entry_point() -> None:
    result = ScoppPipeline().run_map(ROOT / "examples/maps/indoor_lab.yaml")
    assert len(result.mapped.cells) == 109
    assert len(result.clustered.clusters) == 4
    assert len(result.allocation.owner_by_cell) == 109
    assert sum(len(path.cell_ids) for path in result.plan.paths) == 109
    assert result.timings.total_s >= sum((result.timings.auction_s, result.timings.clustering_s, result.timings.discretization_s, result.timings.path_planning_s))


def test_pipeline_applies_typed_configuration() -> None:
    config = ScoppConfig(ClusteringProfile.OFFICIAL_MINIBATCH, random_seed=7, auction_bias=0.25)
    result = ScoppPipeline(config).run_map(ROOT / "examples/maps/indoor_lab.yaml")
    assert result.config is config
    assert result.clustered.profile == "official_minibatch"
    assert result.clustered.random_seed == 7
    assert result.allocation.bias == 0.25
