"""Unified findings normalization and deduplication."""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import Severity

SEVERITY_ORDER = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}

SEVERITY_ALIASES = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "med": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "informational": Severity.INFO,
    "unknown": Severity.INFO,
}


@dataclass
class CanonicalFinding:
    scanner: str
    category: str
    severity: str
    title: str
    description: str
    affected_asset: str
    evidence: str | None = None
    remediation: str | None = None
    references: list[str] = field(default_factory=list)
    compliance_mappings: dict[str, list[str]] = field(default_factory=dict)
    exploitability: str | None = None
    cwe_id: str | None = None
    cve_id: str | None = None
    cvss_score: float | None = None
    raw_data: dict[str, Any] | None = None

    def fingerprint(self) -> str:
        key = f"{self.title}|{self.affected_asset}|{self.cve_id or ''}|{self.cwe_id or ''}"
        return hashlib.sha256(key.encode()).hexdigest()


class FindingsEngine:
    def _severity_rank(self, severity: str) -> int:
        normalized = self.normalize_severity(severity)
        try:
            return SEVERITY_ORDER.get(Severity(normalized), 0)
        except ValueError:
            return 0

    def normalize_severity(self, severity: str) -> str:
        return SEVERITY_ALIASES.get(severity.lower().strip(), Severity.INFO)

    def normalize_url(self, url: str) -> str:
        url = url.strip().lower()
        if url.endswith("/"):
            url = url[:-1]
        return url

    def normalize_host(self, host: str) -> str:
        return host.strip().lower()

    def deduplicate(self, findings: list[CanonicalFinding]) -> list[CanonicalFinding]:
        seen: dict[str, CanonicalFinding] = {}
        for finding in findings:
            fp = finding.fingerprint()
            if fp not in seen:
                seen[fp] = finding
            else:
                existing = seen[fp]
                new_sev = self._severity_rank(finding.severity)
                existing_sev = self._severity_rank(existing.severity)
                if new_sev > existing_sev:
                    seen[fp] = finding
                if finding.evidence and not existing.evidence:
                    existing.evidence = finding.evidence
                if finding.remediation and not existing.remediation:
                    existing.remediation = finding.remediation
        return list(seen.values())

    def merge_raw_findings(self, raw_findings: list[dict[str, Any]]) -> list[CanonicalFinding]:
        canonical = []
        for raw in raw_findings:
            canonical.append(
                CanonicalFinding(
                    scanner=raw.get("scanner", "unknown"),
                    category=raw.get("category", "general"),
                    severity=self.normalize_severity(raw.get("severity", "info")),
                    title=raw.get("title", "Unknown Finding")[:500],
                    description=raw.get("description", "")[:5000],
                    affected_asset=self.normalize_host(raw.get("affected_asset", "")),
                    evidence=raw.get("evidence"),
                    remediation=raw.get("remediation"),
                    references=raw.get("references", []),
                    compliance_mappings=raw.get("compliance_mappings", {}),
                    exploitability=raw.get("exploitability"),
                    cwe_id=raw.get("cwe"),
                    cve_id=raw.get("cve"),
                    cvss_score=raw.get("cvss"),
                    raw_data=raw.get("raw_data"),
                )
            )
        return self.deduplicate(canonical)

    def calculate_risk_score(self, findings: list[CanonicalFinding]) -> float:
        if not findings:
            return 100.0
        weights = {Severity.CRITICAL: 25, Severity.HIGH: 15, Severity.MEDIUM: 8, Severity.LOW: 3, Severity.INFO: 1}
        penalty = sum(weights.get(Severity(f.severity), 1) for f in findings)
        return max(0.0, min(100.0, 100.0 - penalty))
