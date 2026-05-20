"""Integration tests for auth and scan API flows."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_and_me(auth_client: AsyncClient, db_session):
    email = f"integration-{uuid4().hex[:8]}@example.com"
    register_resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecureP@ssw0rd!99",
            "full_name": "Integration User",
            "organization_name": "Integration Org",
        },
    )
    assert register_resp.status_code == 201
    user_data = register_resp.json()
    assert user_data["email"] == email

    login_resp = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "SecureP@ssw0rd!99",
        },
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    token = login_resp.json()["access_token"]
    me_resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["full_name"] == "Integration User"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
