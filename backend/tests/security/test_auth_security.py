"""Authentication security tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_invalid_credentials(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password_rejected(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "full_name": "Test",
            "organization_name": "Org",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_login(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "attacker@example.com",
            "password": "' OR '1'='1' --",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_csrf_protection_on_mutating_requests(client: AsyncClient):
    """Without CSRF header, mutating requests should be blocked (when TESTING is off)."""
    import os

    os.environ["TESTING"] = "false"
    try:
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code in (401, 403)
    finally:
        os.environ["TESTING"] = "true"

