from pathlib import Path

import pytest

from scopp.map.grid import discretize_map
from scopp.map.io import load_map
from scopp.map.schema import parse_map

ROOT = Path(__file__).resolve().parents[2]


def _square(policy: str):
    return parse_map({
        "schema_version": "1.0", "name": "square",
        "coordinates": {"kind": "cartesian", "unit": "m"},
        "aoi": {"exterior": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        "nodes": [{"id": "n1", "position": [1, 1]}],
        "sensor": {"altitude_m": 1, "fov_deg": 90},
        "grid": {"origin": [0, 0], "boundary_policy": policy},
    })


def test_square_discretization_is_deterministic() -> None:
    first = discretize_map(_square("paper_center"))
    second = discretize_map(_square("paper_center"))
    assert first.cells == second.cells
    assert len(first.cells) == 25
    assert first.cells[0].id == "r0_c0"
    assert len(first.cells[0].perimeter_samples) == 32


def test_any_overlap_keeps_partial_boundary_cells() -> None:
    data = _square("any_overlap")
    shifted = parse_map({
        "schema_version": "1.0", "name": "shifted",
        "coordinates": {"kind": "cartesian", "unit": "m"},
        "aoi": {"exterior": [[0.5, 0.5], [9.5, 0.5], [9.5, 9.5], [0.5, 9.5]]},
        "nodes": [{"id": "n1", "position": [1, 1]}],
        "sensor": {"altitude_m": 1, "fov_deg": 90},
        "grid": {"origin": [0, 0], "boundary_policy": "any_overlap"},
    })
    result = discretize_map(shifted)
    assert len(result.cells) == 25
    assert result.cells[0].coverage_ratio == pytest.approx(0.5625)


def test_no_fly_overlap_excludes_cell() -> None:
    result = discretize_map(load_map(ROOT / "examples/maps/arbitrary_terrain.yaml"))
    assert result.cells
    assert any(cell.reason == "intersects_no_fly_zone" for cell in result.rejected_cells)
