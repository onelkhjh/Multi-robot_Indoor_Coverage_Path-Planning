"""Small deterministic polygon primitives needed by map discretization."""

from __future__ import annotations

from math import isfinite

from .models import XY

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


def point_in_ring(point: XY, ring: tuple[XY, ...], *, boundary: bool = True) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) <= EPS and min(x1, x2) - EPS <= x <= max(x1, x2) + EPS and min(y1, y2) - EPS <= y <= max(y1, y2) + EPS:
            return boundary
        if (y1 > y) != (y2 > y):
            intersection_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if intersection_x > x:
                inside = not inside
    return inside


def clip_ring_to_rect(ring: tuple[XY, ...], rect: tuple[float, float, float, float]) -> tuple[XY, ...]:
    """Clip a simple polygon to an axis-aligned cell (Sutherland-Hodgman)."""
    xmin, ymin, xmax, ymax = rect
    output = list(ring)
    boundaries = (
        (lambda p: p[0] >= xmin - EPS, lambda a, b: (xmin, a[1] + (b[1] - a[1]) * (xmin - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= xmax + EPS, lambda a, b: (xmax, a[1] + (b[1] - a[1]) * (xmax - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= ymin - EPS, lambda a, b: (a[0] + (b[0] - a[0]) * (ymin - a[1]) / (b[1] - a[1]), ymin)),
        (lambda p: p[1] <= ymax + EPS, lambda a, b: (a[0] + (b[0] - a[0]) * (ymax - a[1]) / (b[1] - a[1]), ymax)),
    )
    for inside, intersect in boundaries:
        source, output = output, []
        if not source:
            break
        previous = source[-1]
        for current in source:
            current_inside, previous_inside = inside(current), inside(previous)
            if current_inside:
                if not previous_inside:
                    output.append(intersect(previous, current))
                output.append(current)
            elif previous_inside:
                output.append(intersect(previous, current))
            previous = current
    cleaned: list[XY] = []
    for point in output:
        if not cleaned or abs(point[0] - cleaned[-1][0]) > EPS or abs(point[1] - cleaned[-1][1]) > EPS:
            cleaned.append(point)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return tuple(cleaned)


def clipped_area(ring: tuple[XY, ...], rect: tuple[float, float, float, float]) -> tuple[float, tuple[XY, ...]]:
    clipped = clip_ring_to_rect(ring, rect)
    return (abs(signed_area(clipped)) if len(clipped) >= 3 else 0.0, clipped)
