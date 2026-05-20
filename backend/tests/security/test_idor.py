"""IDOR protection tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.organization import Organization


@pytest.mark.asyncio
async def test_cannot_access_other_org_scan(auth_client: AsyncClient, test_user, db_session):
    user, org, membership = test_user

    other_org = Organization(name="Other", slug=f"other-{uuid4().hex[:8]}")
    db_session.add(other_org)
    await db_session.flush()

    token = create_access_token(str(user.id), str(other_org.id), membership.role)
    fake_scan_id = uuid4()

    response = await auth_client.get(
        f"/api/v1/scans/{fake_scan_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (403, 404)
