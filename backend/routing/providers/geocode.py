"""Place search: Photon (komoot) first, Nominatim as a fallback.

Inputs like "41.88, -87.63" are treated as coordinates and never hit an API.
"""
from __future__ import annotations

import re

from django.conf import settings

from .http import ProviderError, get_json

COORD_RE = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


def _label(props: dict) -> str:
    street = " ".join(x for x in (props.get("housenumber"), props.get("street")) if x)
    parts = [props.get("name") or street, props.get("city"), props.get("state"), props.get("country")]
    seen, out = set(), []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return ", ".join(out)


def parse_coordinates(text: str) -> dict | None:
    m = COORD_RE.match(text or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return {"label": f"{lat:.5f}, {lon:.5f}", "lat": lat, "lon": lon}
    return None


def search(text: str, limit: int = 5) -> list[dict]:
    direct = parse_coordinates(text)
    if direct:
        return [direct]
    try:
        data = get_json(
            f"{settings.PHOTON_URL.rstrip('/')}/api/",
            params={"q": text, "limit": limit, "lang": "en"},
            timeout=10,
            what="Geocoding service",
        )
        out = []
        for f in data.get("features", []):
            lon, lat = f["geometry"]["coordinates"][:2]
            out.append({"label": _label(f.get("properties", {})), "lat": lat, "lon": lon})
        if out:
            return out
    except ProviderError:
        pass  # fall through to Nominatim
    data = get_json(
        f"{settings.NOMINATIM_URL.rstrip('/')}/search",
        params={"q": text, "format": "jsonv2", "limit": limit},
        min_interval_s=1.0,
        timeout=10,
        what="Geocoding service",
    )
    return [{"label": r.get("display_name", text), "lat": float(r["lat"]), "lon": float(r["lon"])} for r in data]


def resolve(place) -> dict:
    """Accept {"label","lat","lon"} from the autocomplete, or free text."""
    if isinstance(place, dict) and "lat" in place and "lon" in place:
        lat, lon = float(place["lat"]), float(place["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Coordinates are out of range.")
        return {"label": place.get("label") or f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon}
    text = (place.get("label") if isinstance(place, dict) else place) or ""
    text = str(text).strip()
    if not text:
        raise ValueError("Origin and destination are required.")
    hits = search(text, limit=1)
    if not hits:
        raise ValueError(f'Could not find "{text}". Try a city and state, e.g. "Dallas, TX".')
    return hits[0]
