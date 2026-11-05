"""Hourly forecasts for many points from Open-Meteo (no API key needed).

Units requested: wind in mph, rain and snowfall in inches. Hourly rain/snowfall
are totals for the preceding hour, i.e. an in/h rate, which is what the risk
rules use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from ..geo import LatLon
from .http import ProviderError, get_json

BATCH = 150  # locations per request (URL stays well under limits)
CACHE_TTL_S = 30 * 60


@dataclass
class HourlySeries:
    start: datetime  # UTC, on the hour
    wind: list[float | None]
    gust: list[float | None]
    rain: list[float | None]
    snow: list[float | None]

    def index_for(self, when: datetime) -> int | None:
        """Index of the forecast hour nearest to `when` (None if outside the series)."""
        idx = round((when - self.start).total_seconds() / 3600)
        return idx if 0 <= idx < len(self.wind) else None

    def at(self, when: datetime) -> tuple[float | None, float | None, float | None, float | None]:
        i = self.index_for(when)
        if i is None:
            return None, None, None, None
        return self.wind[i], self.gust[i], self.rain[i], self.snow[i]


def _key(p: LatLon, d0: date, d1: date) -> str:
    return f"om:{p[0]:.2f},{p[1]:.2f}:{d0.isoformat()}:{d1.isoformat()}"


def parse_location(loc: dict) -> HourlySeries:
    hourly = loc.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise ProviderError("Weather service returned no hourly data.")
    start = datetime.fromisoformat(times[0]).replace(tzinfo=timezone.utc)
    n = len(times)

    def col(name):
        values = hourly.get(name) or [None] * n
        return [None if v is None else float(v) for v in values]

    return HourlySeries(start=start, wind=col("wind_speed_10m"), gust=col("wind_gusts_10m"),
                        rain=col("rain"), snow=col("snowfall"))


def fetch_hourly(points: list[LatLon], start: datetime, end: datetime) -> list[HourlySeries | None]:
    """One series per input point (None where the forecast horizon doesn't reach)."""
    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=settings.FORECAST_DAYS - 1)
    d0 = max(start.astimezone(timezone.utc).date(), today)
    d1 = min(end.astimezone(timezone.utc).date(), horizon)
    if d0 > d1:
        return [None] * len(points)

    # Snap to a 0.05 deg (~5 km) grid: finer than the forecast models' own grid,
    # and it de-duplicates nearby checkpoints (shared route sections, dense
    # 10-mile spacing) so a plan stays well inside Open-Meteo's per-minute limit.
    rounded = [(round(lat * 20) / 20, round(lon * 20) / 20) for lat, lon in points]
    results: dict[LatLon, HourlySeries] = {}
    missing: list[LatLon] = []
    for p in dict.fromkeys(rounded):
        hit = cache.get(_key(p, d0, d1))
        if hit is not None:
            results[p] = hit
        else:
            missing.append(p)

    for i in range(0, len(missing), BATCH):
        batch = missing[i:i + BATCH]
        data = get_json(
            f"{settings.OPEN_METEO_URL.rstrip('/')}/v1/forecast",
            params={
                "latitude": ",".join(f"{p[0]:.2f}" for p in batch),
                "longitude": ",".join(f"{p[1]:.2f}" for p in batch),
                "hourly": "wind_speed_10m,wind_gusts_10m,rain,snowfall",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "UTC",
                "start_date": d0.isoformat(),
                "end_date": d1.isoformat(),
            },
            timeout=40,
            what="Weather service",
        )
        if isinstance(data, dict) and data.get("error"):
            raise ProviderError(f"Weather service error: {data.get('reason', 'unknown')}")
        locations = data if isinstance(data, list) else [data]
        if len(locations) != len(batch):
            raise ProviderError("Weather service returned an unexpected number of locations.")
        for p, loc in zip(batch, locations):
            series = parse_location(loc)
            results[p] = series
            cache.set(_key(p, d0, d1), series, CACHE_TTL_S)

    return [results.get(p) for p in rounded]
