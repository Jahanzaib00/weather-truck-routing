"""Small, dependency-free geometry helpers.

Coordinates are always (lat, lon) tuples in degrees; distances are metres
unless a name says otherwise.
"""
from __future__ import annotations

import bisect
import math
from typing import Sequence

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344

LatLon = tuple[float, float]


def haversine_m(a: LatLon, b: LatLon) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def cumulative_distances(coords: Sequence[LatLon]) -> list[float]:
    """Distance from the first vertex to every vertex (len == len(coords))."""
    out = [0.0]
    for prev, cur in zip(coords, coords[1:]):
        out.append(out[-1] + haversine_m(prev, cur))
    return out


def interpolate(coords: Sequence[LatLon], cum: Sequence[float], target_m: float) -> tuple[LatLon, int]:
    """Point at `target_m` along the polyline, plus the index of the segment start."""
    if target_m <= 0:
        return coords[0], 0
    if target_m >= cum[-1]:
        return coords[-1], len(coords) - 2
    i = bisect.bisect_right(cum, target_m) - 1
    seg = cum[i + 1] - cum[i]
    t = 0.0 if seg == 0 else (target_m - cum[i]) / seg
    (la1, lo1), (la2, lo2) = coords[i], coords[i + 1]
    return (la1 + (la2 - la1) * t, lo1 + (lo2 - lo1) * t), i


def interpolate_value(cum: Sequence[float], values: Sequence[float], target_m: float) -> float:
    """Linear interpolation of a per-vertex value (e.g. elapsed seconds) at a distance."""
    if target_m <= 0:
        return values[0]
    if target_m >= cum[-1]:
        return values[-1]
    i = bisect.bisect_right(cum, target_m) - 1
    seg = cum[i + 1] - cum[i]
    t = 0.0 if seg == 0 else (target_m - cum[i]) / seg
    return values[i] + (values[i + 1] - values[i]) * t


def bearing_deg(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination_point(origin: LatLon, bearing: float, distance_m: float) -> LatLon:
    lat1, lon1 = map(math.radians, origin)
    brg = math.radians(bearing)
    d = distance_m / EARTH_RADIUS_M
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brg))
    lon2 = lon1 + math.atan2(
        math.sin(brg) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2)
    )
    return math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180


def simplify(coords: Sequence[LatLon], tolerance_deg: float) -> list[LatLon]:
    """Ramer-Douglas-Peucker (iterative) on lat/lon treated as planar."""
    n = len(coords)
    if n < 3:
        return list(coords)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    tol2 = tolerance_deg * tolerance_deg
    while stack:
        start, end = stack.pop()
        (y1, x1), (y2, x2) = coords[start], coords[end]
        dx, dy = x2 - x1, y2 - y1
        norm = dx * dx + dy * dy
        best_i, best_d = -1, -1.0
        for i in range(start + 1, end):
            y0, x0 = coords[i]
            if norm == 0:
                d = (x0 - x1) ** 2 + (y0 - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / norm))
                d = (x0 - x1 - t * dx) ** 2 + (y0 - y1 - t * dy) ** 2
            if d > best_d:
                best_i, best_d = i, d
        if best_d > tol2 and best_i > 0:
            keep[best_i] = True
            stack.append((start, best_i))
            stack.append((best_i, end))
    return [c for c, k in zip(coords, keep) if k]


def resample(coords: Sequence[LatLon], cum: Sequence[float], step_m: float) -> list[LatLon]:
    """Points every `step_m` metres along a polyline (always includes both ends)."""
    if cum[-1] == 0:
        return [coords[0]]
    count = max(1, int(cum[-1] // step_m))
    pts = [interpolate(coords, cum, k * step_m)[0] for k in range(count + 1)]
    if cum[-1] - count * step_m > 1:
        pts.append(coords[-1])
    return pts


def fast_distance_m(a: LatLon, b: LatLon) -> float:
    """Equirectangular approximation; accurate to <1% under ~200 km."""
    x = math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    y = math.radians(b[0] - a[0])
    return EARTH_RADIUS_M * math.hypot(x, y)


def min_distance_m(p: LatLon, pts: Sequence[LatLon]) -> float:
    return min(fast_distance_m(p, q) for q in pts)


def mercator_y(lat: float) -> float:
    lat = max(-85.0, min(85.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def inverse_mercator_y(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)
