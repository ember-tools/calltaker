"""Distances on the map, close enough for a city: metres per degree and between two points."""

import math

METER_JE_GRAD = 111_320.0


def entfernung(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return the distance in metres between two (latitude, longitude) points."""
    dy = (a[0] - b[0]) * METER_JE_GRAD
    dx = (a[1] - b[1]) * METER_JE_GRAD * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)
