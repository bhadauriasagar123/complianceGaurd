"""Async database session management."""

from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, get_settings

# Query params that asyncpg does not accept (Neon/Railway URLs often include sslmode=)
_ASYNCPG_STRIP_QUERY_KEYS = frozenset({"sslmode", "ssl", "channel_binding", "options"})


def prepare_asyncpg_url(database_url: str) -> tuple[str, dict]:
    """
    Normalize PostgreSQL URLs for asyncpg.
    Strips sslmode from the URL and maps it to connect_args['ssl'].
    """
    if not database_url.startswith("postgresql"):
        return database_url, {}

    parsed = urlparse(database_url)
    query = parse_qs(parsed.query, keep_blank_values=False)
    connect_args: dict = {}

    sslmode = (query.pop("sslmode", ["prefer"])[0] or "prefer").lower()
    for key in _ASYNCPG_STRIP_QUERY_KEYS:
        query.pop(key, None)

    if sslmode in ("require", "verify-ca", "verify-full", "prefer", "allow"):
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False

    # Neon / cloud Postgres typically need SSL even without sslmode in URL
    host = (parsed.hostname or "").lower()
    if not connect_args and ("neon.tech" in host or "railway.app" in host or "render.com" in host):
        connect_args["ssl"] = True

    flat_query = {k: (v[0] if len(v) == 1 else v) for k, v in query.items()}
    new_query = urlencode(flat_query)
    cleaned = urlunparse(parsed._replace(query=new_query))
    return cleaned, connect_args


def build_async_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    database_url, ssl_args = prepare_asyncpg_url(settings.database_url)

    engine_kwargs: dict = {"echo": settings.app_debug}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"timeout": 30}
    else:
        pool_size = settings.database_pool_size
        max_overflow = settings.database_max_overflow
        if settings.is_production:
            pool_size = min(pool_size, 5)
            max_overflow = min(max_overflow, 2)
        engine_kwargs.update(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        connect_args = dict(ssl_args)
        if connect_args:
            engine_kwargs["connect_args"] = connect_args

    return create_async_engine(database_url, **engine_kwargs)


settings = get_settings()
engine = build_async_engine(settings)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            if session.in_transaction():
                await session.commit()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            await session.close()
