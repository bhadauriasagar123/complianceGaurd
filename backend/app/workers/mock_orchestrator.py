"""Mock scan pipeline with real HTTP probes and demo-catalog findings."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.enums import AuditAction, ScanStatus
from app.models.finding import Finding
from app.models.scan import Scan, ScanJob
from app.scanners.base import ScanResult
from app.scanners.http_security_probe import HttpSecurityProbeAdapter
from app.services.audit_service import AuditService
from app.services.compliance_engine import ComplianceEngine
from app.services.demo_findings import get_demo_findings_for_target
from app.services.findings_engine import FindingsEngine

logger = logging.getLogger(__name__)

# Render free tier kills long requests; keep probe under this limit
HTTP_PROBE_TIMEOUT_SECONDS = 12.0


async def _persist_findings(
    db: AsyncSession,
    scan: Scan,
    raw_findings: list[dict],
    *,
    skip_ai: bool = True,
) -> tuple[list, float]:
    engine = FindingsEngine()
    canonical = engine.merge_raw_findings(raw_findings)

    compliance = ComplianceEngine()
    for finding in canonical:
        finding.compliance_mappings = compliance.map_finding(finding)

    if not skip_ai and get_settings().anthropic_api_key:
        from app.services.ai_service import AIService

        ai_service = AIService()
        for finding in canonical[:20]:
            try:
                ai_result = await ai_service.generate_remediation(finding)
                finding.remediation = finding.remediation or ai_result.get("remediation")
            except Exception:
                pass

    for cf in canonical:
        db.add(
            Finding(
                scan_id=scan.id,
                organization_id=scan.organization_id,
                scanner=cf.scanner,
                category=cf.category,
                severity=cf.severity,
                cvss_score=cf.cvss_score,
                title=cf.title,
                description=cf.description,
                affected_asset=cf.affected_asset,
                evidence=cf.evidence,
                remediation=cf.remediation,
                references_json=cf.references,
                compliance_mappings=cf.compliance_mappings,
                exploitability=cf.exploitability,
                cwe_id=cf.cwe_id,
                cve_id=cf.cve_id,
                fingerprint=cf.fingerprint(),
                raw_data=cf.raw_data,
                ai_remediation=cf.remediation,
                ai_confidence=0.85 if cf.remediation else None,
            )
        )

    score = engine.calculate_risk_score(canonical)
    return canonical, score


async def _run_http_probe(target: str) -> ScanResult:
    probe = HttpSecurityProbeAdapter()
    try:
        return await asyncio.wait_for(
            probe.scan(target),
            timeout=HTTP_PROBE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning("http_probe_timeout", target=target)
        return ScanResult(
            scanner="http_probe",
            success=False,
            error=f"HTTP probe timed out after {HTTP_PROBE_TIMEOUT_SECONDS:.0f}s",
        )


async def orchestrate_scan_mock(db: AsyncSession, scan_id: str) -> dict:
    """
    Complete a scan using demo-catalog findings + passive HTTP checks.
    Designed to finish within Render's request time limits.
    """
    result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
    scan = result.scalar_one_or_none()
    if not scan:
        return {"error": "Scan not found"}

    audit = AuditService(db)
    settings = get_settings()
    now = datetime.now(UTC)

    try:
        scan.status = ScanStatus.RUNNING
        scan.started_at = now
        scan.current_phase = "demo_catalog"
        scan.progress_percent = 20
        await db.commit()

        await audit.log(
            AuditAction.SCAN_STARTED,
            organization_id=scan.organization_id,
            user_id=scan.created_by_id,
            resource_id=scan_id,
            details={"mock_pipeline": True, "http_probe": settings.scan_mock_http_probe},
        )

        jobs_result = await db.execute(select(ScanJob).where(ScanJob.scan_id == scan.id))
        jobs = list(jobs_result.scalars().all())
        all_raw: list[dict] = []

        # Demo findings first so scans complete even if outbound HTTP is slow/blocked
        demo = get_demo_findings_for_target(scan.target_value)
        all_raw.extend(demo)

        scan.current_phase = "http_security_probe"
        scan.progress_percent = 50
        await db.commit()

        if settings.scan_mock_http_probe:
            probe_result = await _run_http_probe(scan.target_value)
            if probe_result.success:
                all_raw.extend(probe_result.findings)
                logger.info(
                    "http_probe_complete",
                    scan_id=scan_id,
                    findings=len(probe_result.findings),
                )
            else:
                logger.warning("http_probe_failed", scan_id=scan_id, error=probe_result.error)

        total_jobs = max(len(jobs), 1)
        for idx, job in enumerate(jobs):
            job.status = ScanStatus.COMPLETED
            job.started_at = now
            job.completed_at = datetime.now(UTC)
            job.findings_count = len([f for f in all_raw if f.get("scanner") == job.scanner_type])
            job.error_message = (
                "Mock mode: demo catalog + HTTP probe "
                "(use Docker with SCAN_MOCK_MODE=false for Nmap/Nuclei/ZAP)"
            )[:1000]
            scan.progress_percent = 50 + int((idx + 1) / total_jobs * 30)
            scan.current_phase = f"mock_{job.scanner_type}"

        scan.current_phase = "normalizing"
        scan.progress_percent = 85
        await db.commit()

        canonical, score = await _persist_findings(db, scan, all_raw, skip_ai=True)

        scan.compliance_score = score
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(UTC)
        scan.progress_percent = 100
        scan.current_phase = "completed"
        await db.commit()

        await audit.log(
            AuditAction.SCAN_COMPLETED,
            organization_id=scan.organization_id,
            user_id=scan.created_by_id,
            resource_id=scan_id,
            details={
                "mock_pipeline": True,
                "findings_count": len(canonical),
                "score": scan.compliance_score,
                "http_probe": settings.scan_mock_http_probe,
                "demo_catalog_count": len(demo),
            },
        )
        await db.commit()

        return {
            "scan_id": scan_id,
            "findings": len(canonical),
            "score": scan.compliance_score,
            "mock_pipeline": True,
        }
    except Exception as exc:
        logger.exception("mock_orchestration_failed", scan_id=scan_id)
        scan.status = ScanStatus.FAILED
        scan.error_message = str(exc)[:1000]
        scan.completed_at = datetime.now(UTC)
        scan.current_phase = "failed"
        await db.commit()
        raise
