"""Strict YAML/JSON schema parsing for reproducible map inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

from .geometry import normalize_ring, point_in_polygon, validate_polygon
from .models import (
    CellBoundaryPolicy, CoordinateReference, GridSpec, MapDefinition,
    NodeStart, PolygonSpec, SensorSpec, XY,
)


class MapValidationError(ValueError):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


def _object(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MapValidationError(path, "must be an object")
    return value


def _keys(value: Mapping[str, object], allowed: set[str], required: set[str], path: str) -> None:
    unknown, missing = set(value) - allowed, required - set(value)
    if unknown:
        raise MapValidationError(path, f"unknown fields: {sorted(unknown)}")
    if missing:
        raise MapValidationError(path, f"missing fields: {sorted(missing)}")


def _xy(value: object, path: str) -> XY:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise MapValidationError(path, "must be a two-number coordinate")
    try:
        point = (float(value[0]), float(value[1]))
    except (TypeError, ValueError) as exc:
        raise MapValidationError(path, "must be a two-number coordinate") from exc
    if not all(isfinite(v) for v in point):
        raise MapValidationError(path, "coordinates must be finite")
    return point


def _ring(value: object, path: str) -> tuple[XY, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise MapValidationError(path, "must be a coordinate list")
    try:
        return normalize_ring(tuple(_xy(point, f"{path}/{index}") for index, point in enumerate(value)), path=path)
    except ValueError as exc:
        raise MapValidationError(path, str(exc)) from exc


def _polygon(value: object, path: str) -> PolygonSpec:
    obj = _object(value, path)
    _keys(obj, {"exterior", "holes"}, {"exterior"}, path)
    holes_value = obj.get("holes", [])
    if not isinstance(holes_value, Sequence):
        raise MapValidationError(f"{path}/holes", "must be a list")
    result = PolygonSpec(_ring(obj["exterior"], f"{path}/exterior"), tuple(_ring(h, f"{path}/holes/{i}") for i, h in enumerate(holes_value)))
    try:
        validate_polygon(result, path=path)
    except ValueError as exc:
        raise MapValidationError(path, str(exc)) from exc
    return result


def parse_map(data: Mapping[str, object]) -> MapDefinition:
    root = _object(data, "/")
    allowed = {"schema_version", "name", "coordinates", "aoi", "no_fly_zones", "nodes", "robot_starts", "sensor", "grid"}
    _keys(root, allowed, {"schema_version", "name", "coordinates", "aoi", "sensor", "grid"}, "/")
    if root["schema_version"] != "1.0":
        raise MapValidationError("/schema_version", "only schema version 1.0 is supported")

    coordinates = _object(root["coordinates"], "/coordinates")
    _keys(coordinates, {"kind", "unit"}, {"kind", "unit"}, "/coordinates")
    if coordinates["kind"] != "cartesian":
        raise MapValidationError("/coordinates/kind", "indoor experiments require cartesian coordinates")
    if coordinates["unit"] != "m":
        raise MapValidationError("/coordinates/unit", "must be m")

    sensor_obj = _object(root["sensor"], "/sensor")
    _keys(sensor_obj, {"altitude_m", "fov_deg"}, {"altitude_m", "fov_deg"}, "/sensor")
    sensor = SensorSpec(float(sensor_obj["altitude_m"]), float(sensor_obj["fov_deg"]))

    grid_obj = _object(root["grid"], "/grid")
    _keys(grid_obj, {"origin", "boundary_policy", "perimeter_spacing_m"}, set(), "/grid")
    try:
        policy = CellBoundaryPolicy(str(grid_obj.get("boundary_policy", "paper_center")))
    except ValueError as exc:
        raise MapValidationError("/grid/boundary_policy", "must be paper_center or any_overlap") from exc
    spacing = grid_obj.get("perimeter_spacing_m")
    grid = GridSpec(
        _xy(grid_obj["origin"], "/grid/origin") if "origin" in grid_obj and grid_obj["origin"] is not None else None,
        policy,
        float(spacing) if spacing is not None else None,
    )
    if grid.perimeter_spacing_m is not None and grid.perimeter_spacing_m <= 0:
        raise MapValidationError("/grid/perimeter_spacing_m", "must be greater than zero")

    starts_value = root.get("nodes", root.get("robot_starts", []))
    if not isinstance(starts_value, Sequence):
        raise MapValidationError("/nodes", "must be a list")
    starts: list[NodeStart] = []
    for index, raw in enumerate(starts_value):
        obj = _object(raw, f"/nodes/{index}")
        _keys(obj, {"id", "position"}, {"id", "position"}, f"/nodes/{index}")
        starts.append(NodeStart(str(obj["id"]), _xy(obj["position"], f"/nodes/{index}/position")))
    if len({node.id for node in starts}) != len(starts):
        raise MapValidationError("/nodes", "node ids must be unique")

    zones = root.get("no_fly_zones", [])
    if not isinstance(zones, Sequence):
        raise MapValidationError("/no_fly_zones", "must be a list")
    definition = MapDefinition(
        "1.0", str(root["name"]), CoordinateReference(),
        _polygon(root["aoi"], "/aoi"),
        tuple(_polygon(zone, f"/no_fly_zones/{i}") for i, zone in enumerate(zones)),
        tuple(starts), sensor, grid,
    )
    for node in definition.node_starts:
        if not point_in_polygon(node.position, definition.aoi):
            raise MapValidationError("/nodes", f"node {node.id!r} starts outside the AOI")
    return definition
