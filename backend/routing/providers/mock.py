"""Deterministic offline providers (MOCK_PROVIDERS=1).

Used by the test-suite and for UI work without network access. Routes are
smooth synthetic curves; weather is a storm system drifting east across the
central US so every risk level shows up somewhere.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from ..geo import LatLon, bearing_deg, destination_point, haversine_m
from .openmeteo import HourlySeries

CITIES = {
    "chicago": ("Chicago, Illinois, United States", 41.8781, -87.6298),
    "denver": ("Denver, Colorado, United States", 39.7392, -104.9903),
    "dallas": ("Dallas, Texas, United States", 32.7767, -96.7970),
    "atlanta": ("Atlanta, Georgia, United States", 33.7490, -84.3880),
    "kansas city": ("Kansas City, Missouri, United States", 39.0997, -94.5786),
    "omaha": ("Omaha, Nebraska, United States", 41.2565, -95.9345),
    "st. louis": ("St. Louis, Missouri, United States", 38.6270, -90.1994),
    "minneapolis": ("Minneapolis, Minnesota, United States", 44.9778, -93.2650),
    "memphis": ("Memphis, Tennessee, United States", 35.1495, -90.0490),
    "indianapolis": ("Indianapolis, Indiana, United States", 39.7684, -86.1581),
    "salt lake city": ("Salt Lake City, Utah, United States", 40.7608, -111.8910),
    "los angeles": ("Los Angeles, California, United States", 34.0522, -118.2437),
    "houston": ("Houston, Texas, United States", 29.7604, -95.3698),
    "nashville": ("Nashville, Tennessee, United States", 36.1627, -86.7816),
}


def search(text: str, limit: int = 5) -> list[dict]:
    from .geocode import parse_coordinates

    direct = parse_coordinates(text)
    if direct:
        return [direct]
    q = text.lower().split(",")[0].strip()
    hits = [
        {"label": label, "lat": lat, "lon": lon}
        for key, (label, lat, lon) in CITIES.items()
        if key.startswith(q) or q in key
    ]
    return hits[:limit]


def _curve(a: LatLon, b: LatLon, bulge: float, step_m: float = 2000) -> list[LatLon]:
    """A gentle arc from a to b; `bulge` is the sideways offset as a fraction of length."""
    length = haversine_m(a, b)
    n = max(2, int(length // step_m))
    brg = bearing_deg(a, b)
    pts = []
    for i in range(n + 1):
        t = i / n
        base = destination_point(a, brg, length * t)
        off = math.sin(math.pi * t) * bulge * length + math.sin(t * 9) * 3000
        pts.append(destination_point(base, brg + 90, off) if off else base)
    return pts


def _speed_mps(t: float, length_m: float, pos_m: float) -> float:
    urban = pos_m < 12_000 or length_m - pos_m < 12_000
    mph = 32 if urban else 62 + 6 * math.sin(t * 17)
    return mph * 0.44704


def fetch_routes(points: list[LatLon], alternatives: int = 0):
    from .osrm import RawRoute

    def build(path_pts: list[LatLon], bulge: float) -> RawRoute:
        coords: list[LatLon] = []
        for a, b in zip(path_pts, path_pts[1:]):
            seg = _curve(a, b, bulge)
            coords.extend(seg if not coords else seg[1:])
        dists = [haversine_m(p, q) for p, q in zip(coords, coords[1:])]
        total = sum(dists)
        durs, pos = [], 0.0
        for i, d in enumerate(dists):
            durs.append(d / _speed_mps(i / len(dists), total, pos))
            pos += d
        return RawRoute(coords, dists, durs, total, sum(durs))

    routes = [build(points, 0.03)]
    if alternatives and len(points) == 2:
        routes.append(build(points, -0.12))  # like OSRM: often only 2 options
    return routes


def _storm(lat: float, lon: float, when: datetime) -> tuple[float, float, float, float]:
    t0 = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hours = (when - t0).total_seconds() / 3600
    centre = destination_point((40.2, -100.5), 75, 40_000 * hours)  # drifts ENE at 40 km/h
    d = haversine_m((lat, lon), centre)
    g = math.exp(-((d / 230_000) ** 2))
    wind = 9 + 50 * g + 3 * math.sin(lat * 3 + lon * 2 + hours / 3)
    cold = lat >= 41.0
    rain = 0.0 if cold else max(0.0, 1.05 * g - 0.02)
    snow = max(0.0, 3.2 * g - 0.1) if cold else 0.0
    return round(wind, 1), round(wind * 1.45, 1), round(rain, 3), round(snow, 3)


def fetch_hourly(points: list[LatLon], start: datetime, end: datetime):
    s = start.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    e = end.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    hours = int((e - s).total_seconds() // 3600)
    out = []
    for lat, lon in points:
        cols = [_storm(lat, lon, s + timedelta(hours=h)) for h in range(hours)]
        out.append(HourlySeries(start=s, wind=[c[0] for c in cols], gust=[c[1] for c in cols],
                                rain=[c[2] for c in cols], snow=[c[3] for c in cols]))
    return out
