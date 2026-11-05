"""Provider facade: the planner calls these and never imports a concrete API module."""
from __future__ import annotations

from django.conf import settings

from . import geocode, mock, openmeteo, osrm
from .http import ProviderError  # noqa: F401  (re-export)


def fetch_routes(points, alternatives=0):
    return (mock if settings.MOCK_PROVIDERS else osrm).fetch_routes(points, alternatives)


def fetch_hourly(points, start, end):
    return (mock if settings.MOCK_PROVIDERS else openmeteo).fetch_hourly(points, start, end)


def search_places(text, limit=5):
    return (mock if settings.MOCK_PROVIDERS else geocode).search(text, limit)


def resolve_place(place):
    if settings.MOCK_PROVIDERS and not (isinstance(place, dict) and "lat" in place):
        text = place.get("label") if isinstance(place, dict) else place
        hits = mock.search(str(text or ""), 1)
        if not hits:
            raise ValueError(f'Could not find "{text}".')
        return hits[0]
    return geocode.resolve(place)
