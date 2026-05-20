"""Scan orchestration service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, ScanStatus
from app.models.scan import Scan, ScanJob
from app.models.target import AuthorizedTarget
from app.services.audit_service import AuditService
from app.services.target_validation import TargetValidationError, TargetValidator


class ScanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.validator = TargetValidator()

    async def create_scan(
        self,
        organization_id: UUID,
        user_id: UUID,
        authorized_target_id: UUID,
        scan_type: str,
        scanners_enabled: list[str],
        consent_confirmed: bool,
        ip_address: str | None = None,
    ) -> Scan:
        if not consent_confirmed:
            raise ValueError("Scan consent must be confirmed")

        target_result = await self.db.execute(
            select(AuthorizedTarget).where(
                AuthorizedTarget.id == authorized_target_id,
                AuthorizedTarget.organization_id == organization_id,
                AuthorizedTarget.is_active == True,  # noqa: E712
            )
        )
        target = target_result.scalar_one_or_none()
        if not target:
            raise ValueError("Authorized target not found")

        if target.expires_at and target.expires_at < datetime.now(UTC):
            raise ValueError("Target authorization has expired")

        try:
            self.validator.validate(target.target_value, target.target_type)
        except TargetValidationError as exc:
            raise ValueError(exc.message) from exc

        hour_ago = datetime.now(UTC).replace(microsecond=0)
        from datetime import timedelta

        count_result = await self.db.execute(
            select(func.count(Scan.id)).where(
                Scan.organization_id == organization_id,
                Scan.created_at >= hour_ago - timedelta(hours=1),
            )
        )
        scan_count = count_result.scalar() or 0
        from app.core.config import get_settings

        if scan_count >= get_settings().scan_rate_limit_per_hour:
            raise ValueError("Scan rate limit exceeded for organization")

        scan = Scan(
            organization_id=organization_id,
            created_by_id=user_id,
            authorized_target_id=authorized_target_id,
            target_value=target.normalized_target,
            scan_type=scan_type,
            status=ScanStatus.PENDING,
            scanners_enabled=scanners_enabled,
            consent_confirmed=True,
            consent_confirmed_at=datetime.now(UTC),
        )
        self.db.add(scan)
        await self.db.flush()

        for scanner in scanners_enabled:
            job = ScanJob(scan_id=scan.id, scanner_type=scanner, status=ScanStatus.PENDING)
            self.db.add(job)

        await self.db.flush()

        await self.audit.log(
            AuditAction.SCAN_CREATED,
            organization_id=organization_id,
            user_id=user_id,
            resource_type="scan",
            resource_id=str(scan.id),
            ip_address=ip_address,
            details={"target": target.normalized_target, "scanners": scanners_enabled},
        )

        return scan

    async def get_scan(self, scan_id: UUID, organization_id: UUID) -> Scan | None:
        result = await self.db.execute(
            select(Scan).where(Scan.id == scan_id, Scan.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def list_scans(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Scan], int]:
        query = select(Scan).where(Scan.organization_id == organization_id)
        count_query = select(func.count(Scan.id)).where(Scan.organization_id == organization_id)

        if status:
            query = query.where(Scan.status == status)
            count_query = count_query.where(Scan.status == status)

        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(Scan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        scans = (await self.db.execute(query)).scalars().all()
        return list(scans), total

    async def cancel_scan(self, scan_id: UUID, organization_id: UUID, user_id: UUID) -> Scan:
        scan = await self.get_scan(scan_id, organization_id)
        if not scan:
            raise ValueError("Scan not found")
        if scan.status in (ScanStatus.COMPLETED, ScanStatus.CANCELLED):
            raise ValueError("Scan cannot be cancelled")

        scan.status = ScanStatus.CANCELLED
        await self.audit.log(
            AuditAction.SCAN_CANCELLED,
            organization_id=organization_id,
            user_id=user_id,
            resource_id=str(scan_id),
        )
        return scan
