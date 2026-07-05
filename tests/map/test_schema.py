from pathlib import Path

import pytest

from scopp.map.io import load_map
from scopp.map.models import CellBoundaryPolicy
from scopp.map.schema import MapValidationError, parse_map

ROOT = Path(__file__).resolve().parents[2]


def test_load_paper_example() -> None:
    value = load_map(ROOT / "examples/maps/paper_like.yaml")
    assert value.grid.boundary_policy is CellBoundaryPolicy.PAPER_CENTER
    assert [node.id for node in value.node_starts] == ["node-01", "node-02"]


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(MapValidationError, match="unknown fields"):
        parse_map({"schema_version": "1.0", "name": "x", "unexpected": True})


def test_geographic_coordinates_are_out_of_scope() -> None:
    data = {
        "schema_version": "1.0", "name": "geo",
        "coordinates": {"kind": "geographic", "unit": "deg"},
        "aoi": {"exterior": [[0, 0], [1, 0], [0, 1]]},
        "sensor": {"altitude_m": 1, "fov_deg": 60}, "grid": {},
    }
    with pytest.raises(MapValidationError, match="indoor experiments require cartesian"):
        parse_map(data)
