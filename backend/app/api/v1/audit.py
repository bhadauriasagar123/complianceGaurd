"""Audit log API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserContext, require_permission
from app.core.database import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    message: str | None
    created_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("/logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[CurrentUserContext, Depends(require_permission("audit:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = None,
) -> list[AuditLogResponse]:
    query = select(AuditLog).where(AuditLog.organization_id == current_user.organization_id)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            outcome=log.outcome,
            message=log.message,
        )
        for log in logs
    ]
