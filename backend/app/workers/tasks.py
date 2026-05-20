"""Celery scan orchestration tasks."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory as SyncSession
from app.domain.enums import AuditAction, ScanStatus
from app.models.finding import Finding
from app.models.scan import Scan, ScanJob
from app.scanners import get_scanner
from app.services.audit_service import AuditService
from app.services.compliance_engine import ComplianceEngine
from app.services.findings_engine import FindingsEngine
from app.workers.celery_app import celery_app
from app.workers.mock_orchestrator import orchestrate_scan_mock


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="orchestrate_scan", max_retries=2)
def orchestrate_scan(self, scan_id: str) -> dict:
    return run_async(_orchestrate_scan(scan_id))


async def _orchestrate_scan_dev_mock(scan_id: str) -> dict:
    """Passive HTTP probe + demo catalog (no Nmap/Nuclei/ZAP required)."""
    async with SyncSession() as db:
        return await orchestrate_scan_mock(db, scan_id)


async def _orchestrate_scan(scan_id: str) -> dict:
    if get_settings().use_scan_mock:
        return await _orchestrate_scan_dev_mock(scan_id)

    async with SyncSession() as db:
        result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            return {"error": "Scan not found"}

        audit = AuditService(db)
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.now(UTC)
        scan.current_phase = "initializing"
        await db.commit()

        await audit.log(
            AuditAction.SCAN_STARTED,
            organization_id=scan.organization_id,
            user_id=scan.created_by_id,
            resource_id=scan_id,
        )

        all_raw_findings: list[dict] = []
        jobs_result = await db.execute(select(ScanJob).where(ScanJob.scan_id == scan.id))
        jobs = jobs_result.scalars().all()
        total_jobs = len(jobs)

        for idx, job in enumerate(jobs):
            scan.current_phase = f"running_{job.scanner_type}"
            scan.progress_percent = int((idx / total_jobs) * 70)
            job.status = ScanStatus.RUNNING
            job.started_at = datetime.now(UTC)
            await db.commit()

            try:
                scanner = get_scanner(job.scanner_type)
                scan_result = await scanner.scan(scan.target_value)
                job.status = ScanStatus.COMPLETED if scan_result.success else ScanStatus.FAILED
                job.findings_count = len(scan_result.findings)
                job.completed_at = datetime.now(UTC)
                if scan_result.error:
                    job.error_message = scan_result.error[:1000]
                all_raw_findings.extend(scan_result.findings)
            except Exception as exc:
                job.status = ScanStatus.FAILED
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(UTC)

            await db.commit()

        scan.current_phase = "normalizing"
        scan.progress_percent = 75
        await db.commit()

        engine = FindingsEngine()
        canonical = engine.merge_raw_findings(all_raw_findings)

        scan.current_phase = "compliance_mapping"
        scan.progress_percent = 85
        compliance = ComplianceEngine()
        for finding in canonical:
            finding.compliance_mappings = compliance.map_finding(finding)

        scan.current_phase = "ai_processing"
        scan.progress_percent = 90
        await db.commit()

        from app.services.ai_service import AIService

        ai_service = AIService()
        for finding in canonical[:50]:
            try:
                ai_result = await ai_service.generate_remediation(finding)
                finding.remediation = finding.remediation or ai_result.get("remediation")
            except Exception:
                pass

        for cf in canonical:
            db_finding = Finding(
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
                ai_confidence=0.85,
            )
            db.add(db_finding)

        scan.compliance_score = engine.calculate_risk_score(canonical)
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(UTC)
        scan.progress_percent = 100
        scan.current_phase = "completed"
        await db.commit()

        from app.services.report_service import ReportService

        report_service = ReportService(db)
        await report_service.generate_pdf_report(
            scan_id=scan.id,
            organization_id=scan.organization_id,
            user_id=scan.created_by_id,
        )

        await audit.log(
            AuditAction.SCAN_COMPLETED,
            organization_id=scan.organization_id,
            user_id=scan.created_by_id,
            resource_id=scan_id,
            details={"findings_count": len(canonical), "score": scan.compliance_score},
        )

        return {"scan_id": scan_id, "findings": len(canonical), "score": scan.compliance_score}
