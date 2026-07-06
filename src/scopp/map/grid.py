"""SCoPP pseudo-discretization into equal square cells."""

from __future__ import annotations

from math import ceil, floor

from shapely.geometry import Point, box
from shapely.ops import unary_union

from .footprint import coverage_width
from .geometry import EPS, geometry_to_specs, polygon_from_spec
from .models import CellBoundaryPolicy, CoverageCell, DiscretizedMap, MapDefinition, RejectedCell, XY


def _cell_id(row: int, col: int) -> str:
    def part(value: int) -> str:
        return f"m{abs(value)}" if value < 0 else str(value)
    return f"r{part(row)}_c{part(col)}"


def _perimeter(vertices: tuple[XY, XY, XY, XY], width: float, requested: float) -> tuple[XY, ...]:
    count = max(1, ceil(width / requested))
    result: list[XY] = []
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        for index in range(count):
            t = index / count
            result.append((start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])))
    return tuple(result)


def discretize_map(definition: MapDefinition) -> DiscretizedMap:
    """Create deterministic equal-width cells from a SCoPP map definition."""
    width = coverage_width(definition.sensor.altitude_m, definition.sensor.fov_deg)
    spacing = definition.grid.perimeter_spacing_m or width / 8.0
    aoi = definition.aoi.exterior
    aoi_geometry = polygon_from_spec(definition.aoi)
    no_fly_geometry = unary_union(tuple(polygon_from_spec(zone) for zone in definition.no_fly_zones))
    xmin, ymin = min(p[0] for p in aoi), min(p[1] for p in aoi)
    xmax, ymax = max(p[0] for p in aoi), max(p[1] for p in aoi)
    origin = definition.grid.origin or (xmin, ymin)
    col_min, col_max = floor((xmin - origin[0]) / width), ceil((xmax - origin[0]) / width)
    row_min, row_max = floor((ymin - origin[1]) / width), ceil((ymax - origin[1]) / width)
    cells: list[CoverageCell] = []
    rejected: list[RejectedCell] = []

    for row in range(row_min, row_max):
        for col in range(col_min, col_max):
            x0, y0 = origin[0] + col * width, origin[1] + row * width
            rect = (x0, y0, x0 + width, y0 + width)
            center = (x0 + width / 2, y0 + width / 2)
            vertices = ((x0, y0), (x0 + width, y0), (x0 + width, y0 + width), (x0, y0 + width))
            cell_geometry = box(*rect)
            coverage_geometry = cell_geometry.intersection(aoi_geometry)
            aoi_area = coverage_geometry.area
            no_fly_area = cell_geometry.intersection(no_fly_geometry).area if not no_fly_geometry.is_empty else 0.0
            center_valid = aoi_geometry.covers(Point(center))
            accepted_by_aoi = center_valid if definition.grid.boundary_policy is CellBoundaryPolicy.PAPER_CENTER else aoi_area > EPS
            if not accepted_by_aoi:
                rejected.append(RejectedCell(row, col, center, "outside_aoi"))
                continue
            if no_fly_area > EPS:
                rejected.append(RejectedCell(row, col, center, "intersects_no_fly_zone"))
                continue
            cells.append(CoverageCell(
                _cell_id(row, col), row, col, center, vertices, geometry_to_specs(coverage_geometry),
                min(1.0, aoi_area / (width * width)), _perimeter(vertices, width, spacing),
            ))
    return DiscretizedMap(definition, width, tuple(cells), tuple(rejected))
