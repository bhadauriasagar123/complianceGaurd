"""Compliance framework mapping engine."""

from app.domain.enums import ComplianceFramework
from app.services.findings_engine import CanonicalFinding

CONTROL_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "sql_injection": {
        ComplianceFramework.OWASP_TOP_10: ["A03:2021-Injection"],
        ComplianceFramework.PCI_DSS: ["6.5.1"],
        ComplianceFramework.HIPAA: ["164.312(a)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "xss": {
        ComplianceFramework.OWASP_TOP_10: ["A03:2021-Injection"],
        ComplianceFramework.PCI_DSS: ["6.5.7"],
        ComplianceFramework.HIPAA: ["164.312(e)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "authentication": {
        ComplianceFramework.OWASP_TOP_10: ["A07:2021-Identification and Authentication Failures"],
        ComplianceFramework.PCI_DSS: ["8.3"],
        ComplianceFramework.HIPAA: ["164.312(d)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "encryption": {
        ComplianceFramework.OWASP_TOP_10: ["A02:2021-Cryptographic Failures"],
        ComplianceFramework.PCI_DSS: ["4.1"],
        ComplianceFramework.HIPAA: ["164.312(e)(2)(ii)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "access_control": {
        ComplianceFramework.OWASP_TOP_10: ["A01:2021-Broken Access Control"],
        ComplianceFramework.PCI_DSS: ["7.1"],
        ComplianceFramework.HIPAA: ["164.312(a)(1)"],
        ComplianceFramework.GDPR: ["Art. 25"],
    },
    "vulnerability": {
        ComplianceFramework.OWASP_TOP_10: ["A06:2021-Vulnerable and Outdated Components"],
        ComplianceFramework.PCI_DSS: ["6.2"],
        ComplianceFramework.HIPAA: ["164.308(a)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "service_discovery": {
        ComplianceFramework.OWASP_TOP_10: ["A05:2021-Security Misconfiguration"],
        ComplianceFramework.PCI_DSS: ["2.2"],
        ComplianceFramework.HIPAA: ["164.312(a)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "web": {
        ComplianceFramework.OWASP_TOP_10: ["A05:2021-Security Misconfiguration"],
        ComplianceFramework.PCI_DSS: ["6.5"],
        ComplianceFramework.HIPAA: ["164.312(e)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
    "general": {
        ComplianceFramework.OWASP_TOP_10: ["A05:2021-Security Misconfiguration"],
        ComplianceFramework.PCI_DSS: ["6.1"],
        ComplianceFramework.HIPAA: ["164.308(a)(1)"],
        ComplianceFramework.GDPR: ["Art. 32"],
    },
}

SEVERITY_CONTROL_IMPACT: dict[str, float] = {
    "critical": 25.0,
    "high": 15.0,
    "medium": 8.0,
    "low": 3.0,
    "info": 0.5,
}


class ComplianceEngine:
    def map_finding(self, finding: CanonicalFinding) -> dict[str, list[str]]:
        category = finding.category.lower() if finding.category else "general"
        for key in CONTROL_MAPPINGS:
            if key in category:
                return CONTROL_MAPPINGS[key]
        if finding.cve_id:
            return CONTROL_MAPPINGS["vulnerability"]
        return CONTROL_MAPPINGS.get(category, CONTROL_MAPPINGS["general"])

    def calculate_framework_scores(
        self,
        findings: list[CanonicalFinding],
        framework: ComplianceFramework,
    ) -> dict:
        total_controls = len({c for mappings in CONTROL_MAPPINGS.values() for c in mappings.get(framework, [])})
        failed_controls: set[str] = set()

        for finding in findings:
            mappings = finding.compliance_mappings or self.map_finding(finding)
            controls = mappings.get(framework, [])
            if finding.severity in ("critical", "high", "medium"):
                failed_controls.update(controls)

        passed = total_controls - len(failed_controls)
        score = (passed / total_controls * 100) if total_controls > 0 else 100.0

        return {
            "framework": framework,
            "score": round(score, 2),
            "total_controls": total_controls,
            "passed_controls": passed,
            "failed_controls": list(failed_controls),
            "status": "pass" if score >= 80 else "fail",
        }

    def calculate_all_scores(self, findings: list[CanonicalFinding]) -> dict[str, dict]:
        return {
            fw.value: self.calculate_framework_scores(findings, fw)
            for fw in ComplianceFramework
        }
