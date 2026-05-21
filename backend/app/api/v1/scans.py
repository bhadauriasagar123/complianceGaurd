"""Scan and target API routes."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import OperationalError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserContext, require_permission
from app.core.database import get_db
from app.models.finding import Finding
from app.models.target import AuthorizedTarget
from app.schemas.scan import (
    AuthorizedTargetCreate,
    AuthorizedTargetResponse,
    FindingResolutionGuideResponse,
    FindingResponse,
    ScanCreateRequest,
    ScanListResponse,
    ScanResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.scan_service import ScanService
from app.services.target_validation import TargetValidator
from app.workers.mock_orchestrator import orchestrate_scan_mock
from app.workers.queue import enqueue_scan
from app.workers.scan_failures import mark_scan_failed

logger = get_logger(__name__)
MOCK_SCAN_TIMEOUT_SECONDS = 90.0

router = APIRouter(tags=["Scans"])


@router.post(
    "/targets",
    response_model=AuthorizedTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    body: AuthorizedTargetCreate,
    request: Request,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("target:write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthorizedTargetResponse:
    from datetime import UTC, datetime

    from app.domain.enums import AuditAction
    from app.services.audit_service import AuditService

    validator = TargetValidator()
    try:
        normalized = validator.validate(body.target_value, body.target_type)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    target = AuthorizedTarget(
        organization_id=current_user.organization_id,
        created_by_id=current_user.user_id,
        target_value=body.target_value,
        target_type=body.target_type,
        normalized_target=normalized,
        ownership_proof=body.ownership_proof,
        consent_recorded_at=datetime.now(UTC),
        consent_recorded_by=current_user.user_id,
        verification_method=body.verification_method,
        notes=body.notes,
    )
    db.add(target)
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        AuditAction.TARGET_AUTHORIZED,
        organization_id=current_user.organization_id,
        user_id=current_user.user_id,
        resource_id=str(target.id),
        ip_address=request.client.host if request.client else None,
        details={"target": normalized},
    )
    return AuthorizedTargetResponse.model_validate(target)


@router.get("/targets", response_model=list[AuthorizedTargetResponse])
async def list_targets(
    current_user: Annotated[CurrentUserContext, Depends(require_permission("target:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AuthorizedTargetResponse]:
    result = await db.execute(
        select(AuthorizedTarget).where(
            AuthorizedTarget.organization_id == current_user.organization_id,
            AuthorizedTarget.is_active == True,  # noqa: E712
        )
    )
    return [AuthorizedTargetResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("scan:execute"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScanResponse:
    service = ScanService(db)
    try:
        scan = await service.create_scan(
            organization_id=current_user.organization_id,
            user_id=current_user.user_id,
            authorized_target_id=body.authorized_target_id,
            scan_type=body.scan_type.value,
            scanners_enabled=[s.value for s in body.scanners_enabled],
            consent_confirmed=body.consent_confirmed,
            ip_address=request.client.host if request.client else None,
        )
        scan_id = str(scan.id)

        # Mock scans run inline on the request DB session (Render free tier has no background workers)
        if get_settings().use_scan_mock:
            try:
                await asyncio.wait_for(
                    orchestrate_scan_mock(db, scan_id),
                    timeout=MOCK_SCAN_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.error("mock_scan_timeout", scan_id=scan_id)
                await mark_scan_failed(
                    scan_id,
                    "Scan timed out on the server. Cancel and start one scan at a time.",
                )
            except Exception as exc:
                logger.exception("mock_scan_failed", scan_id=scan_id, error=str(exc))
                await mark_scan_failed(scan_id, str(exc))
            await db.refresh(scan)
        else:
            await db.commit()
            enqueue_scan(scan_id, background_tasks)

        return ScanResponse.model_validate(scan)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OperationalError as exc:
        if "locked" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is busy processing another scan. Please retry in a few seconds.",
            ) from exc
        raise


@router.get("/scans", response_model=ScanListResponse)
async def list_scans(
    current_user: Annotated[CurrentUserContext, Depends(require_permission("scan:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> ScanListResponse:
    service = ScanService(db)
    scans, total = await service.list_scans(
        current_user.organization_id, page=page, page_size=page_size, status=status
    )
    return ScanListResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: UUID,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("scan:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScanResponse:
    service = ScanService(db)
    scan = await service.get_scan(scan_id, current_user.organization_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return ScanResponse.model_validate(scan)


@router.post("/scans/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: UUID,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("scan:write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScanResponse:
    service = ScanService(db)
    try:
        scan = await service.cancel_scan(scan_id, current_user.organization_id, current_user.user_id)
        return ScanResponse.model_validate(scan)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/scans/{scan_id}/findings", response_model=list[FindingResponse])
async def get_findings(
    scan_id: UUID,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("finding:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    severity: str | None = None,
) -> list[FindingResponse]:
    query = select(Finding).where(
        Finding.scan_id == scan_id,
        Finding.organization_id == current_user.organization_id,
    )
    if severity:
        query = query.where(Finding.severity == severity)
    result = await db.execute(query.order_by(Finding.severity))
    return [FindingResponse.model_validate(f) for f in result.scalars().all()]


@router.post(
    "/scans/{scan_id}/findings/{finding_id}/resolution-guide",
    response_model=FindingResolutionGuideResponse,
)
async def get_finding_resolution_guide(
    scan_id: UUID,
    finding_id: UUID,
    current_user: Annotated[CurrentUserContext, Depends(require_permission("finding:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingResolutionGuideResponse:
    from app.services.ai_service import AIService
    from app.services.findings_engine import CanonicalFinding

    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.scan_id == scan_id,
            Finding.organization_id == current_user.organization_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    canonical = CanonicalFinding(
        scanner=finding.scanner,
        category=finding.category,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        affected_asset=finding.affected_asset,
        evidence=finding.evidence,
        remediation=finding.remediation,
        cwe_id=finding.cwe_id,
        cve_id=finding.cve_id,
        cvss_score=finding.cvss_score,
    )

    ai_service = AIService()
    guide = await ai_service.generate_resolution_guide(canonical)

    finding.ai_remediation = guide.get("summary") or finding.ai_remediation
    finding.ai_confidence = guide.get("confidence", finding.ai_confidence)
    await db.commit()

    return FindingResolutionGuideResponse(
        finding_id=finding.id,
        summary=guide["summary"],
        priority=guide["priority"],
        estimated_effort=guide["estimated_effort"],
        steps=guide["steps"],
        compliance_notes=guide["compliance_notes"],
        confidence=guide["confidence"],
        powered_by_ai=guide.get("powered_by_ai", False),
        ai_provider=guide.get("ai_provider"),
    )
