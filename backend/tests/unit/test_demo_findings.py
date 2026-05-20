"""Tests for demo practice-site findings catalog."""

from app.services.demo_findings import get_demo_findings_for_target, host_matches_pattern


def test_host_matches_wildcard():
    assert host_matches_pattern("testphp.vulnweb.com", "*.vulnweb.com")
    assert host_matches_pattern("foo.vulnweb.com", "*.vulnweb.com")
    assert not host_matches_pattern("evil.com", "*.vulnweb.com")


def test_vulnweb_demo_findings():
    findings = get_demo_findings_for_target("https://testphp.vulnweb.com/artists.php")
    assert len(findings) >= 3
    assert any("SQL injection" in f["title"] for f in findings)


def test_juice_shop_demo_findings():
    findings = get_demo_findings_for_target("https://demo.owasp-juice.shop")
    assert len(findings) >= 2


def test_unknown_host_no_demo_findings():
    assert get_demo_findings_for_target("https://example.com") == []
