import pytest
from shapely.geometry import MultiPolygon, Polygon

from scopp.map.geometry import geometry_to_specs
from scopp.map.grid import discretize_map
from scopp.map.schema import MapValidationError, parse_map


def _map(aoi, *, no_fly=()):
    return parse_map({
        "schema_version": "1.0", "name": "geometry",
        "coordinates": {"kind": "cartesian", "unit": "m"},
        "aoi": aoi, "no_fly_zones": list(no_fly),
        "nodes": [{"id": "n", "position": [0.25, 0.25]}],
        "sensor": {"altitude_m": 1, "fov_deg": 90},
        "grid": {"origin": [0, 0], "boundary_policy": "any_overlap"},
    })


def test_self_intersecting_aoi_is_rejected() -> None:
    with pytest.raises(MapValidationError, match="positive area|invalid"):
        _map({"exterior": [[0, 0], [2, 2], [0, 2], [2, 0]]})


def test_aoi_hole_removes_fully_inside_cell() -> None:
    mapped = discretize_map(_map({
        "exterior": [[0, 0], [6, 0], [6, 6], [0, 6]],
        "holes": [[[2, 2], [4, 2], [4, 4], [2, 4]]],
    }))
    assert "r1_c1" not in {cell.id for cell in mapped.cells}
    assert any(cell.reason == "outside_aoi" for cell in mapped.rejected_cells)


def test_overlapping_no_fly_zones_are_unioned() -> None:
    mapped = discretize_map(_map(
        {"exterior": [[0, 0], [6, 0], [6, 6], [0, 6]]},
        no_fly=(
            {"exterior": [[1, 1], [4, 1], [4, 4], [1, 4]]},
            {"exterior": [[2, 2], [5, 2], [5, 5], [2, 5]]},
        ),
    ))
    assert mapped.cells
    assert any(cell.reason == "intersects_no_fly_zone" for cell in mapped.rejected_cells)


def test_multipolygon_coverage_preserves_all_components() -> None:
    geometry = MultiPolygon((
        Polygon(((0, 0), (1, 0), (1, 1), (0, 1))),
        Polygon(((2, 0), (3, 0), (3, 1), (2, 1))),
    ))
    specs = geometry_to_specs(geometry)
    assert len(specs) == 2
