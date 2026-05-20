"""Report download API routes."""

import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserContext, require_permission
from app.core.config import get_settings
from app.core.database import get_db
from app.models.report import Report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/scan/{scan_id}")
async def download_scan_report(
    scan_id: UUID,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("report:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    result = await db.execute(
        select(Report).where(
            Report.scan_id == scan_id,
            Report.organization_id == current_user.organization_id,
        ).order_by(Report.created_at.desc())
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    settings = get_settings()
    safe_path = os.path.realpath(report.file_path)
    base_path = os.path.realpath(settings.report_storage_path)
    if not safe_path.startswith(base_path):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid report path")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file missing")

    return FileResponse(
        safe_path,
        media_type="application/pdf",
        filename=f"complianceguard-report-{scan_id}.pdf",
        headers={"X-Content-Type-Options": "nosniff"},
    )
