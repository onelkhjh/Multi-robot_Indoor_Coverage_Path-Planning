"""Validated Shapely adapters for AOI and cell geometry operations."""

from __future__ import annotations

from math import isfinite

from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

from .models import PolygonSpec, XY

EPS = 1e-12


def signed_area(points: tuple[XY, ...]) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])) / 2


def normalize_ring(points: tuple[XY, ...], *, path: str) -> tuple[XY, ...]:
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3 or len(set(points)) < 3:
        raise ValueError(f"{path} must contain at least three distinct vertices")
    if not all(isfinite(value) for point in points for value in point):
        raise ValueError(f"{path} coordinates must be finite")
    area = signed_area(points)
    if abs(area) <= EPS:
        raise ValueError(f"{path} must have positive area")
    return points if area > 0 else tuple(reversed(points))


def polygon_from_spec(spec: PolygonSpec) -> Polygon:
    return Polygon(spec.exterior, holes=spec.holes)


def validate_polygon(spec: PolygonSpec, *, path: str) -> None:
    polygon = polygon_from_spec(spec)
    if polygon.is_empty or polygon.area <= EPS:
        raise ValueError(f"{path} must have positive area")
    if not polygon.is_valid:
        raise ValueError(f"{path} is invalid: {explain_validity(polygon)}")


def point_in_polygon(point: XY, spec: PolygonSpec, *, boundary: bool = True) -> bool:
    polygon = polygon_from_spec(spec)
    candidate = Point(point)
    return polygon.covers(candidate) if boundary else polygon.contains(candidate)


def valid_polygonal(geometry: BaseGeometry) -> BaseGeometry:
    """Return valid polygonal content without silently retaining lines/points."""
    fixed = make_valid(geometry)
    if isinstance(fixed, (Polygon, MultiPolygon)):
        return fixed
    if isinstance(fixed, GeometryCollection):
        polygons = [part for part in fixed.geoms if isinstance(part, (Polygon, MultiPolygon))]
        from shapely.ops import unary_union
        return unary_union(polygons)
    return Polygon()


def geometry_to_specs(geometry: BaseGeometry) -> tuple[PolygonSpec, ...]:
    polygonal = valid_polygonal(geometry)
    if polygonal.is_empty:
        return ()
    polygons = (polygonal,) if isinstance(polygonal, Polygon) else tuple(polygonal.geoms)
    return tuple(
        PolygonSpec(
            tuple((float(x), float(y)) for x, y in polygon.exterior.coords[:-1]),
            tuple(tuple((float(x), float(y)) for x, y in ring.coords[:-1]) for ring in polygon.interiors),
        )
        for polygon in polygons
    )
