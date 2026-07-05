"""Camera-footprint calculations from SCoPP Section III-B."""

from math import isfinite, radians, tan


def coverage_width(altitude_m: float, fov_deg: float) -> float:
    """Return paper cell width ``W = 2 h tan(F / 2)`` in metres."""
    if not isfinite(altitude_m) or altitude_m <= 0:
        raise ValueError("altitude_m must be finite and greater than zero")
    if not isfinite(fov_deg) or not 0 < fov_deg < 180:
        raise ValueError("fov_deg must be finite and between 0 and 180 degrees")
    return 2.0 * altitude_m * tan(radians(fov_deg) / 2.0)
