import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import providers
from .heatmap import build_heatmap
from .planner import build_plan

log = logging.getLogger(__name__)


def _error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@csrf_exempt
@require_POST
def plan(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _error("Invalid JSON body.", 400)
    try:
        return JsonResponse(build_plan(data))
    except ValueError as exc:
        return _error(str(exc), 400)
    except providers.ProviderError as exc:
        return _error(str(exc), exc.status)
    except Exception:  # pragma: no cover - last-resort guard
        log.exception("plan failed")
        return _error("Something went wrong while planning the trip.", 500)


@require_GET
def heatmap(request, plan_id: str):
    ctx = cache.get(f"plan:{plan_id}")
    if ctx is None:
        return _error("This plan has expired. Please plan the trip again.", 404)
    try:
        return JsonResponse(build_heatmap(ctx))
    except providers.ProviderError as exc:
        return _error(str(exc), exc.status)


@require_GET
def geocode(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"results": []})
    try:
        return JsonResponse({"results": providers.search_places(q, 5)})
    except providers.ProviderError as exc:
        return _error(str(exc), exc.status)


@require_GET
def health(request):
    return JsonResponse({"ok": True, "mock_providers": settings.MOCK_PROVIDERS})


def spa(request, path=""):
    """Serve the built React app for every non-API path."""
    index = Path(settings.FRONTEND_DIST) / "index.html"
    if index.exists():
        return FileResponse(open(index, "rb"), content_type="text/html")
    return HttpResponse("Frontend not built. Run `npm run build` in frontend/ (or use the Vite dev server).",
                        content_type="text/plain")
