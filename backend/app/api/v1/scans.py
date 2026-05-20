"""Scan and target API routes."""

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
    FindingResponse,
    ScanCreateRequest,
    ScanListResponse,
    ScanResponse,
)
from app.services.scan_service import ScanService
from app.services.target_validation import TargetValidator
from app.workers.queue import enqueue_scan

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
        response = ScanResponse.model_validate(scan)
        enqueue_scan(str(scan.id), background_tasks)
        return response
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
