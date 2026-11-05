import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-secret")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "routing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}  # stateless app: no models
APPEND_SLASH = False

# Built React app: Docker copies it to backend/frontend_dist; locally it's frontend/dist.
_default_dist = BASE_DIR / "frontend_dist"
if not _default_dist.exists():
    _default_dist = BASE_DIR.parent / "frontend" / "dist"
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", _default_dist))

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None  # serves /assets/*, favicon, etc.

# File cache so the plan -> heatmap hand-off works across gunicorn workers.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.environ.get("CACHE_DIR", "/tmp/truck-routing-cache"),
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

USE_TZ = True
TIME_ZONE = "UTC"

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ---- External services (all free, no API keys) ----
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
OSRM_MIN_INTERVAL_S = float(os.environ.get("OSRM_MIN_INTERVAL_S", "1.0"))  # demo server policy: 1 req/s
OPEN_METEO_URL = os.environ.get("OPEN_METEO_URL", "https://api.open-meteo.com")
PHOTON_URL = os.environ.get("PHOTON_URL", "https://photon.komoot.io")
NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
HTTP_USER_AGENT = os.environ.get("HTTP_USER_AGENT", "weather-aware-truck-routing/1.0 (+https://github.com/Jahanzaib00/weather-truck-routing)")
MOCK_PROVIDERS = env_bool("MOCK_PROVIDERS", False)

# ---- Model parameters ----
FORECAST_DAYS = 16  # Open-Meteo forecast horizon
TRUCK_MAX_SPEED_MPH = float(os.environ.get("TRUCK_MAX_SPEED_MPH", "65"))
DISPLAY_SIMPLIFY_DEG = 0.0006  # ~60 m: route geometry sent to the browser
HEATMAP_MAX_POINTS = int(os.environ.get("HEATMAP_MAX_POINTS", "180"))
