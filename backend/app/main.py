"""ComplianceGuard FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import configure_logging, get_logger
from app.middleware.security import CSRFMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware, issue_csrf_token

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

REQUEST_COUNT = Counter("cg_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("cg_http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_application", env=settings.app_env)
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("PRAGMA journal_mode=WAL"))
        logger.info("sqlite_schema_ready")
    yield
    logger.info("shutting_down_application")


app = FastAPI(
    title="ComplianceGuard API",
    description="AI-powered infrastructure compliance and security assessment platform",
    version="1.0.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
_cors_kwargs: dict = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
    "max_age": 600,
}
# Allow Vercel production + preview URLs when hosting frontend on Vercel
if settings.is_production:
    _cors_kwargs["allow_origin_regex"] = r"https://[\w-]+\.vercel\.app"

app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.include_router(api_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    endpoint = request.url.path
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
    return response


@app.get("/health")
async def health_check(response: Response) -> dict:
    csrf_token = issue_csrf_token(response)
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.app_env,
        "csrf_token": csrf_token,
    }


@app.get("/metrics")
async def metrics() -> Response:
    if not settings.prometheus_enabled:
        return JSONResponse({"detail": "Metrics disabled"}, status_code=404)
    return Response(content=generate_latest(), media_type="text/plain")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from sqlalchemy.exc import OperationalError

    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    if isinstance(exc, OperationalError) and "locked" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database busy. Retry in a moment, or restart the API server.",
            },
        )
    detail = "Internal server error"
    if settings.app_env == "development":
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})
