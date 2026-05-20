"""CORS helpers for SPA clients (Vercel) calling the API on another domain."""

import re

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

# Vercel production + preview deployments
VERCEL_ORIGIN_RE = re.compile(r"^https://[\w-]+\.vercel\.app$", re.IGNORECASE)

CORS_ALLOW_HEADERS = "Authorization, Content-Type, X-CSRF-Token, X-Request-ID"
CORS_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


def is_origin_allowed(origin: str | None) -> bool:
    if not origin:
        return False
    origin = origin.rstrip("/")
    settings = get_settings()
    allowed = {o.rstrip("/") for o in settings.cors_origins_list}
    if origin in allowed:
        return True
    return bool(VERCEL_ORIGIN_RE.fullmatch(origin))


def apply_cors_headers(request: Request, response: Response) -> None:
    """Ensure error responses (500/403) still include CORS headers for browsers."""
    origin = request.headers.get("origin")
    if origin and is_origin_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers.setdefault("Vary", "Origin")


def cors_preflight_response(request: Request) -> Response | None:
    """Handle OPTIONS preflight for allowed origins."""
    if request.method != "OPTIONS":
        return None
    origin = request.headers.get("origin")
    if not origin or not is_origin_allowed(origin):
        return None
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
            "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
            "Access-Control-Max-Age": "600",
            "Vary": "Origin",
        },
    )
