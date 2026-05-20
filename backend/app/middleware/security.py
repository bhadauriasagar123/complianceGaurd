"""Security middleware - headers, request ID, CSRF."""

import secrets
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.cors_utils import apply_cors_headers
from app.core.logging import request_id_var


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        settings = get_settings()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        if settings.is_production or settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        rid = request_id_var.get() or str(uuid.uuid4())
        response.headers["X-Request-ID"] = rid

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(rid)
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


CSRF_COOKIE_NAME = "cg_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def issue_csrf_token(response: Response) -> str:
    """Set CSRF cookie on response and return the token (for SPA cross-origin clients)."""
    token = secrets.token_urlsafe(32)
    settings = get_settings()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return token


class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next) -> Response:
        import os

        if os.environ.get("TESTING", "").lower() in ("true", "1", "yes"):
            return await call_next(request)

        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            resp = Response(
                content='{"detail":"CSRF token missing"}',
                status_code=403,
                media_type="application/json",
            )
            apply_cors_headers(request, resp)
            return resp

        if not secrets.compare_digest(cookie_token, header_token):
            resp = Response(
                content='{"detail":"CSRF token invalid"}',
                status_code=403,
                media_type="application/json",
            )
            apply_cors_headers(request, resp)
            return resp

        return await call_next(request)
