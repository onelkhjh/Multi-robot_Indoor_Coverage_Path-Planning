"""Map input and pseudo-discretization for SCoPP."""

from .footprint import coverage_width
from .grid import discretize_map
from .io import load_map
from .models import CellBoundaryPolicy, CoverageCell, DiscretizedMap, MapDefinition

__all__ = [
    "CellBoundaryPolicy",
    "CoverageCell",
    "DiscretizedMap",
    "MapDefinition",
    "coverage_width",
    "discretize_map",
    "load_map",
]
