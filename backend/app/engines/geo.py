"""Distance and route helpers (pure functions).

All road figures are ESTIMATES derived from straight-line distance; they are
labelled as such everywhere (PRD 3.6 / 13.2 step 4). No paid routing API.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

EARTH_RADIUS_KM = 6371.0
ROAD_FACTOR = 1.25          # straight line -> typical road distance in Western/Central Europe
COACH_AVG_KMH = 70.0        # door-to-door average incl. city traffic
BREAK_EVERY_H = 4.5         # EU driver rules: 45 min break after 4.5 h driving
BREAK_MIN = 45


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def road_km(a: tuple[float, float], b: tuple[float, float]) -> int:
    """Estimated road distance (km)."""
    return round(haversine_km(a, b) * ROAD_FACTOR)


def drive_minutes(km: float) -> int:
    """Estimated coach travel time incl. mandatory breaks (minutes)."""
    hours = km / COACH_AVG_KMH
    breaks = int(hours // BREAK_EVERY_H)
    return round(hours * 60 + breaks * BREAK_MIN)


def route_length(points: Sequence[tuple[float, float]], order: Sequence[int]) -> float:
    return sum(haversine_km(points[order[i]], points[order[i + 1]]) for i in range(len(order) - 1))


def order_route(points: Sequence[tuple[float, float]], start: int | None = None, end: int | None = None) -> list[int]:
    """Short visiting order through all points with optional fixed start/end.

    Nearest-neighbour construction followed by 2-opt improvement on the inner
    section (start/end stay fixed). Deterministic for a given input.
    """
    n = len(points)
    if n <= 1:
        return list(range(n))
    remaining = [i for i in range(n) if i not in (start, end)]
    current = start if start is not None else min(remaining, key=lambda i: (points[i][1], points[i][0]))  # west-most
    if start is None:
        remaining.remove(current)
    order = [current]
    while remaining:
        nxt = min(remaining, key=lambda i: (haversine_km(points[current], points[i]), i))
        order.append(nxt)
        remaining.remove(nxt)
        current = nxt
    if end is not None and end != start:
        order.append(end)

    # 2-opt on the section that may move
    lo = 1 if start is not None else 0
    hi = len(order) - (1 if end is not None and end != start else 0)
    improved = True
    while improved:
        improved = False
        for i in range(lo, hi - 1):
            for j in range(i + 1, hi):
                candidate = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if route_length(points, candidate) + 1e-9 < route_length(points, order):
                    order, improved = candidate, True
    return order
