"""Unit tests for rule-based finding resolution guides."""

from app.services.finding_resolution import build_rule_based_resolution_guide
from app.services.findings_engine import CanonicalFinding


def _finding(**kwargs) -> CanonicalFinding:
    defaults = {
        "scanner": "http_probe",
        "category": "headers",
        "severity": "medium",
        "title": "Test finding",
        "description": "Test description",
        "affected_asset": "https://example.com",
    }
    defaults.update(kwargs)
    return CanonicalFinding(**defaults)


def test_hsts_guide_includes_header_steps():
    guide = build_rule_based_resolution_guide(
        _finding(title="Missing Strict-Transport-Security header")
    )
    assert "HSTS" in guide["summary"]
    assert len(guide["steps"]) >= 3
    assert guide["powered_by_ai"] is False
    assert guide["steps"][0]["order"] == 1


def test_sqli_guide_uses_cwe():
    guide = build_rule_based_resolution_guide(
        _finding(title="Possible injection", description="param", cwe_id="CWE-89", severity="high")
    )
    assert guide["priority"] == "high"
    assert "SQL injection" in guide["summary"]
    assert any("parameter" in s["title"].lower() for s in guide["steps"])


def test_generic_fallback_uses_remediation_hint():
    hint = "Rotate API keys and restrict IP allow-list."
    guide = build_rule_based_resolution_guide(
        _finding(title="Misconfigured API gateway", remediation=hint)
    )
    assert hint in guide["steps"][1]["description"]
    assert guide["summary"] == hint
