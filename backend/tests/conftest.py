"""Pytest configuration and fixtures."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Set test environment before any app imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long-for-jwt-signing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "8vP2mKqR9xT4nW7jL1hF5sY0bN6cA3eU=")

# Clear settings cache after forcing test env
def _clear_settings_cache() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()


_clear_settings_cache()

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.domain.enums import UserRole
from app.main import app
from app.models.organization import Organization, OrganizationMember
from app.models.user import User

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

_engine_kwargs: dict = {"echo": False}
if not TEST_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(pool_pre_ping=True)
engine = create_async_engine(TEST_DATABASE_URL, **_engine_kwargs)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    with patch("app.workers.tasks.orchestrate_scan") as mock_task:
        mock_task.delay = MagicMock(return_value=None)
        yield mock_task


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> tuple[User, Organization, OrganizationMember]:
    org = Organization(name="Test Org", slug=f"test-org-{uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"test-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecureP@ssw0rd!99"),
        full_name="Test User",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=UserRole.ORG_ADMIN,
    )
    db_session.add(membership)
    await db_session.flush()
    return user, org, membership


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Client with CSRF cookie/header for mutating requests."""
    response = await client.get("/health")
    csrf_token = response.cookies.get("cg_csrf_token", "test-csrf-token")
    client.headers.update({"X-CSRF-Token": csrf_token})
    return client
