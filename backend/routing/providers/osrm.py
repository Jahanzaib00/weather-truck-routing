"""Driving routes from an OSRM server (default: the public demo server)."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from ..geo import LatLon, haversine_m
from .http import ProviderError, get_json


@dataclass
class RawRoute:
    coords: list[LatLon]  # (lat, lon) vertices
    seg_dist_m: list[float]  # len == len(coords) - 1
    seg_dur_s: list[float]  # car-profile duration per segment
    distance_m: float
    duration_s: float


def parse_route(route: dict) -> RawRoute:
    coords = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    seg_dist = [haversine_m(a, b) for a, b in zip(coords, coords[1:])]
    total_dist = sum(seg_dist) or 1.0

    durations: list[float] = []
    for leg in route.get("legs", []):
        durations.extend((leg.get("annotation") or {}).get("duration") or [])

    if len(durations) != len(seg_dist):
        # Leg joins can make annotation and geometry lengths differ; spread the
        # total duration by distance instead of mis-aligning per-segment speeds.
        durations = [route["duration"] * d / total_dist for d in seg_dist]

    return RawRoute(
        coords=coords,
        seg_dist_m=seg_dist,
        seg_dur_s=[float(x) for x in durations],
        distance_m=float(route["distance"]),
        duration_s=float(route["duration"]),
    )


def fetch_routes(points: list[LatLon], alternatives: int = 0) -> list[RawRoute]:
    path = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
    params = {
        "overview": "full",
        "geometries": "geojson",
        "annotations": "distance,duration",
        "steps": "false",
    }
    if alternatives:
        params["alternatives"] = str(alternatives)
    data = get_json(
        f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{path}",
        params=params,
        min_interval_s=settings.OSRM_MIN_INTERVAL_S,
        what="Routing service",
    )
    code = data.get("code")
    if code == "NoRoute":
        return []
    if code != "Ok":
        raise ProviderError(f"Routing service error: {data.get('message') or code}")
    return [parse_route(r) for r in data.get("routes", [])]
