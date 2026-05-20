"""Outermost CORS layer so 403/500 responses still include Access-Control-Allow-Origin."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.cors_utils import apply_cors_headers, cors_preflight_response


class CorsFallbackMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        preflight = cors_preflight_response(request)
        if preflight is not None:
            return preflight

        response = await call_next(request)
        apply_cors_headers(request, response)
        return response
