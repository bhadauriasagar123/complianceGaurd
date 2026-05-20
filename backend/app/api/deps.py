"""FastAPI dependencies for auth and authorization."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.domain.enums import has_permission
from app.models.organization import OrganizationMember
from app.models.user import User


@dataclass
class CurrentUserContext:
    user_id: UUID
    email: str
    organization_id: UUID
    role: str
    permissions: set[str]


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> CurrentUserContext:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])
    role = payload["role"]

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")

    user_result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.locked_until and user.locked_until > user.updated_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked")

    from app.domain.enums import ROLE_PERMISSIONS

    return CurrentUserContext(
        user_id=user_id,
        email=user.email,
        organization_id=org_id,
        role=role,
        permissions=ROLE_PERMISSIONS.get(role, set()),
    )


def require_permission(permission: str):
    async def checker(current_user: Annotated[CurrentUserContext, Depends(get_current_user)]) -> CurrentUserContext:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return checker


async def get_optional_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUserContext | None:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
