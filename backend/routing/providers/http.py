"""Shared HTTP session: retries on 429/5xx, a polite User-Agent, per-host throttling."""
from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ProviderError(Exception):
    """An upstream API failed or returned something unusable."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


_session: requests.Session | None = None
_lock = threading.Lock()
_last_call: dict[str, float] = {}


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
        s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=10))
        s.mount("http://", HTTPAdapter(max_retries=retry, pool_maxsize=10))
        s.headers["User-Agent"] = settings.HTTP_USER_AGENT
        _session = s
    return _session


def get_json(url: str, *, params=None, min_interval_s: float = 0.0, timeout: float = 25.0, what: str = "API"):
    """GET a JSON document. `min_interval_s` spaces out calls to the same host
    (the public OSRM and Nominatim servers ask for at most 1 request/second)."""
    if min_interval_s:
        host = urlparse(url).netloc
        with _lock:
            wait = _last_call.get(host, 0.0) + min_interval_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _last_call[host] = time.monotonic()
    try:
        resp = session().get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise ProviderError(f"{what} is unreachable ({exc.__class__.__name__}). Please try again.") from exc
    if resp.status_code == 429:
        raise ProviderError(f"{what} rate limit reached. Please wait a minute and try again.", status=503)
    if resp.status_code >= 500:
        raise ProviderError(f"{what} is having problems (HTTP {resp.status_code}). Please try again.")
    try:
        return resp.json()
    except ValueError as exc:
        raise ProviderError(f"{what} returned an invalid response (HTTP {resp.status_code}).") from exc
