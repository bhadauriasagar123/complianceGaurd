"""Findings engine unit tests."""

from app.services.findings_engine import CanonicalFinding, FindingsEngine


def test_deduplicate_merges_same_fingerprint():
    engine = FindingsEngine()
    findings = [
        CanonicalFinding(
            scanner="nuclei",
            category="web",
            severity="high",
            title="SQL Injection",
            description="desc",
            affected_asset="https://example.com",
            cve_id="CVE-2024-0001",
        ),
        CanonicalFinding(
            scanner="zap",
            category="web",
            severity="medium",
            title="SQL Injection",
            description="desc2",
            affected_asset="https://example.com",
            cve_id="CVE-2024-0001",
        ),
    ]
    result = engine.deduplicate(findings)
    assert len(result) == 1
    assert result[0].severity == "high"


def test_risk_score_calculation():
    engine = FindingsEngine()
    findings = [
        CanonicalFinding("n", "c", "critical", "t", "d", "a"),
        CanonicalFinding("n", "c", "high", "t", "d", "a"),
    ]
    score = engine.calculate_risk_score(findings)
    assert score < 100
    assert score >= 0


def test_normalize_severity():
    engine = FindingsEngine()
    assert engine.normalize_severity("CRITICAL") == "critical"
    assert engine.normalize_severity("informational") == "info"
