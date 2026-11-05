"""Weather grid along the trip corridor for hours 0-48 after departure.

The grid is regular in Web-Mercator space (equal-width columns, rows evenly
spaced in Mercator y), so the frontend can draw it as one image overlay that
lines up exactly with the map. Only cells near a route are fetched; the rest
stay transparent. All 49 hours ship in one response, so the slider never waits
on the network.
"""
from __future__ import annotations

import math
from datetime import timedelta

from django.conf import settings

from . import providers
from .geo import LatLon, fast_distance_m, inverse_mercator_y, mercator_y

HOURS = 48


def _corridor_cells(bbox, samples: list[LatLon], cell_deg: float, near_m: float):
    s, w, n, e = bbox
    nx = max(2, math.ceil((e - w) / cell_deg))
    y_top, y_bottom = mercator_y(n), mercator_y(s)
    cell_y = math.radians(cell_deg)
    ny = max(2, math.ceil((y_top - y_bottom) / cell_y))
    east = w + nx * cell_deg
    y_bottom = y_top - ny * cell_y

    bucket = max(cell_deg, near_m / 111_000)
    grid: dict[tuple[int, int], list[LatLon]] = {}
    for p in samples:
        grid.setdefault((int(p[0] // bucket), int(p[1] // bucket)), []).append(p)

    cells, centers = [], []
    for row in range(ny):
        lat = inverse_mercator_y(y_top - (row + 0.5) * cell_y)
        for col in range(nx):
            lon = w + (col + 0.5) * cell_deg
            bi, bj = int(lat // bucket), int(lon // bucket)
            if any(
                fast_distance_m((lat, lon), q) <= near_m
                for di in (-1, 0, 1) for dj in (-1, 0, 1)
                for q in grid.get((bi + di, bj + dj), ())
            ):
                cells.append(row * nx + col)
                centers.append((lat, lon))
    bounds = [[inverse_mercator_y(y_bottom), w], [n, east]]
    return nx, ny, cells, centers, bounds


def build_heatmap(ctx: dict) -> dict:
    s, w, n, e = ctx["bbox"]
    pad = max(0.4, 0.12 * max(n - s, e - w))
    bbox = (max(-80.0, s - pad), max(-180.0, w - pad), min(80.0, n + pad), min(180.0, e + pad))

    cell_deg = max(0.15, (bbox[3] - bbox[1]) / 30, (bbox[2] - bbox[0]) / 30)
    while True:
        near_m = max(60_000.0, 1.2 * cell_deg * 111_000)
        nx, ny, cells, centers, bounds = _corridor_cells(bbox, ctx["samples"], cell_deg, near_m)
        if len(centers) <= settings.HEATMAP_MAX_POINTS:
            break
        cell_deg *= 1.2

    start = ctx["departure"].replace(minute=0, second=0, microsecond=0)
    series = providers.fetch_hourly(centers, start, start + timedelta(hours=HOURS))
    times = [start + timedelta(hours=h) for h in range(HOURS + 1)]

    wind, rain, snow = [], [], []
    for sr in series:
        cw, cr, cs = [], [], []
        for t in times:
            v = sr.at(t) if sr else (None, None, None, None)
            cw.append(None if v[0] is None else round(v[0], 1))
            cr.append(None if v[2] is None else round(v[2], 3))
            cs.append(None if v[3] is None else round(v[3], 3))
        wind.append(cw)
        rain.append(cr)
        snow.append(cs)

    return {
        "bounds": bounds,
        "nx": nx,
        "ny": ny,
        "cells": cells,
        "times": [t.isoformat().replace("+00:00", "Z") for t in times],
        "wind_mph": wind,
        "rain_in": rain,
        "snow_in": snow,
    }
