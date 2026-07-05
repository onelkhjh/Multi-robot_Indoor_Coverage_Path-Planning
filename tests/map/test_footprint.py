from math import sqrt

import pytest

from scopp.map.footprint import coverage_width


def test_paper_footprint_equation() -> None:
    assert coverage_width(10.0, 60.0) == pytest.approx(20.0 / sqrt(3))


@pytest.mark.parametrize("altitude,fov", [(0, 60), (-1, 60), (10, 0), (10, 180)])
def test_invalid_footprint_inputs(altitude: float, fov: float) -> None:
    with pytest.raises(ValueError):
        coverage_width(altitude, fov)
