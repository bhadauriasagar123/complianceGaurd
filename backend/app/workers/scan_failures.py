"""Mark scans failed when orchestration times out or crashes."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.domain.enums import ScanStatus
from app.models.scan import Scan, ScanJob


async def mark_scan_failed(scan_id: str, error_message: str) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            return
        if scan.status in (ScanStatus.COMPLETED, ScanStatus.CANCELLED):
            return

        now = datetime.now(UTC)
        scan.status = ScanStatus.FAILED
        scan.error_message = error_message[:1000]
        scan.completed_at = now
        scan.current_phase = "failed"
        scan.progress_percent = scan.progress_percent or 0

        jobs_result = await db.execute(select(ScanJob).where(ScanJob.scan_id == scan.id))
        for job in jobs_result.scalars().all():
            if job.status not in (ScanStatus.COMPLETED, ScanStatus.CANCELLED):
                job.status = ScanStatus.FAILED
                job.completed_at = now
                job.error_message = error_message[:1000]

        await db.commit()
