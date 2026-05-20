"""Immutable audit logging service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, get_request_id
from app.domain.enums import AuditAction
from app.models.audit import AuditLog

logger = get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        action: AuditAction | str,
        *,
        organization_id: UUID | None = None,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
        outcome: str = "success",
        message: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=str(action),
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            details=details,
            outcome=outcome,
            trace_id=get_request_id(),
            message=message,
        )
        self.db.add(entry)
        await self.db.flush()

        logger.info(
            "audit_event",
            action=str(action),
            user_id=str(user_id) if user_id else None,
            org_id=str(organization_id) if organization_id else None,
            outcome=outcome,
        )
        return entry
