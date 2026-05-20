"""PDF report generation with injection protections."""

import hashlib
import os
from datetime import UTC, datetime
from uuid import UUID

import bleach
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.enums import AuditAction, ComplianceFramework
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.report import Report
from app.models.scan import Scan
from app.services.ai_service import AIService
from app.services.audit_service import AuditService
from app.services.compliance_engine import ComplianceEngine
from app.services.findings_engine import CanonicalFinding


def sanitize_text(text: str | None, max_length: int = 5000) -> str:
    if not text:
        return ""
    text = text[:max_length]
    return bleach.clean(text, tags=[], strip=True)


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.audit = AuditService(db)

    async def generate_pdf_report(
        self,
        scan_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Report:
        scan_result = await self.db.execute(
            select(Scan).where(Scan.id == scan_id, Scan.organization_id == organization_id)
        )
        scan = scan_result.scalar_one()

        org_result = await self.db.execute(select(Organization).where(Organization.id == organization_id))
        org = org_result.scalar_one()

        findings_result = await self.db.execute(select(Finding).where(Finding.scan_id == scan_id))
        db_findings = findings_result.scalars().all()

        canonical = [
            CanonicalFinding(
                scanner=f.scanner,
                category=f.category,
                severity=f.severity,
                title=f.title,
                description=f.description,
                affected_asset=f.affected_asset,
                evidence=f.evidence,
                remediation=f.remediation or f.ai_remediation,
                cwe_id=f.cwe_id,
                cve_id=f.cve_id,
                cvss_score=f.cvss_score,
                compliance_mappings=f.compliance_mappings,
            )
            for f in db_findings
        ]

        compliance = ComplianceEngine()
        framework_scores = compliance.calculate_all_scores(canonical)

        ai_service = AIService()
        severity_counts = {}
        for f in canonical:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        exec_summary = await ai_service.generate_executive_summary(
            [{"title": f.title, "severity": f.severity} for f in canonical[:10]],
            framework_scores,
        )

        os.makedirs(self.settings.report_storage_path, exist_ok=True)
        filename = f"report_{scan_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.settings.report_storage_path, filename)

        self._build_pdf(filepath, org.name, scan, canonical, framework_scores, exec_summary, severity_counts)

        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        report = Report(
            organization_id=organization_id,
            scan_id=scan_id,
            created_by_id=user_id,
            report_type="compliance_assessment",
            file_path=filepath,
            file_hash=file_hash,
            frameworks=[fw.value for fw in ComplianceFramework],
            metadata_json={
                "findings_count": len(canonical),
                "compliance_score": scan.compliance_score,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(report)
        await self.db.flush()

        await self.audit.log(
            AuditAction.REPORT_GENERATED,
            organization_id=organization_id,
            user_id=user_id,
            resource_id=str(report.id),
        )
        return report

    def _build_pdf(
        self,
        filepath: str,
        org_name: str,
        scan: Scan,
        findings: list[CanonicalFinding],
        framework_scores: dict,
        exec_summary: dict,
        severity_counts: dict,
    ) -> None:
        doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=24, textColor=colors.HexColor("#1a365d"))
        elements = []

        elements.append(Paragraph(sanitize_text(f"ComplianceGuard Security Report - {org_name}"), title_style))
        elements.append(Spacer(1, 0.25 * inch))
        elements.append(Paragraph(sanitize_text(f"Target: {scan.target_value}"), styles["Normal"]))
        elements.append(Paragraph(sanitize_text(f"Scan Date: {scan.started_at or scan.created_at}"), styles["Normal"]))
        elements.append(Paragraph(sanitize_text(f"Compliance Score: {scan.compliance_score or 'N/A'}"), styles["Normal"]))
        elements.append(Spacer(1, 0.25 * inch))

        elements.append(Paragraph("Executive Summary", styles["Heading2"]))
        elements.append(Paragraph(sanitize_text(exec_summary.get("summary", "")), styles["Normal"]))
        elements.append(Spacer(1, 0.25 * inch))

        elements.append(Paragraph("Severity Distribution", styles["Heading2"]))
        sev_data = [["Severity", "Count"]] + [[k, str(v)] for k, v in severity_counts.items()]
        sev_table = Table(sev_data, colWidths=[2 * inch, 1.5 * inch])
        sev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(sev_table)
        elements.append(Spacer(1, 0.25 * inch))

        elements.append(Paragraph("Compliance Framework Scores", styles["Heading2"]))
        fw_data = [["Framework", "Score", "Status"]]
        for fw, scores in framework_scores.items():
            fw_data.append([fw, str(scores.get("score", "N/A")), scores.get("status", "N/A")])
        fw_table = Table(fw_data, colWidths=[2 * inch, 1 * inch, 1 * inch])
        fw_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(fw_table)
        elements.append(Spacer(1, 0.25 * inch))

        elements.append(Paragraph("Findings Detail", styles["Heading2"]))
        for finding in findings[:50]:
            elements.append(Paragraph(
                sanitize_text(f"<b>[{finding.severity.upper()}]</b> {finding.title}"),
                styles["Normal"],
            ))
            elements.append(Paragraph(sanitize_text(finding.description[:500]), styles["BodyText"]))
            if finding.remediation:
                elements.append(Paragraph(
                    sanitize_text(f"Remediation: {finding.remediation[:300]}"),
                    styles["Italic"],
                ))
            elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements)
