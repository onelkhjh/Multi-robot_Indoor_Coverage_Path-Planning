"""Immutable map-domain models shared by all SCoPP stages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

XY = tuple[float, float]


class CellBoundaryPolicy(str, Enum):
    """Project policies; the paper does not specify boundary-cell handling."""

    PAPER_CENTER = "paper_center"
    ANY_OVERLAP = "any_overlap"


@dataclass(frozen=True, slots=True)
class CoordinateReference:
    unit: str = "m"


@dataclass(frozen=True, slots=True)
class PolygonSpec:
    exterior: tuple[XY, ...]
    holes: tuple[tuple[XY, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class NodeStart:
    id: str
    position: XY


@dataclass(frozen=True, slots=True)
class SensorSpec:
    altitude_m: float
    fov_deg: float


@dataclass(frozen=True, slots=True)
class GridSpec:
    origin: XY | None = None
    boundary_policy: CellBoundaryPolicy = CellBoundaryPolicy.PAPER_CENTER
    perimeter_spacing_m: float | None = None


@dataclass(frozen=True, slots=True)
class MapDefinition:
    schema_version: str
    name: str
    coordinates: CoordinateReference
    aoi: PolygonSpec
    no_fly_zones: tuple[PolygonSpec, ...]
    node_starts: tuple[NodeStart, ...]
    sensor: SensorSpec
    grid: GridSpec


@dataclass(frozen=True, slots=True)
class CoverageCell:
    id: str
    row: int
    col: int
    center: XY
    vertices: tuple[XY, XY, XY, XY]
    coverage_geometry: tuple[PolygonSpec, ...]
    coverage_ratio: float
    perimeter_samples: tuple[XY, ...]


@dataclass(frozen=True, slots=True)
class RejectedCell:
    row: int
    col: int
    center: XY
    reason: str


@dataclass(frozen=True, slots=True)
class DiscretizedMap:
    source: MapDefinition
    cell_width_m: float
    cells: tuple[CoverageCell, ...]
    rejected_cells: tuple[RejectedCell, ...]
