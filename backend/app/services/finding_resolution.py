"""Rule-based resolution guides when AI API is unavailable."""

from app.services.findings_engine import CanonicalFinding


def _steps(*items: tuple[str, str, str]) -> list[dict]:
    return [
        {"order": i + 1, "title": t, "description": d, "verification": v}
        for i, (t, d, v) in enumerate(items)
    ]


def build_rule_based_resolution_guide(finding: CanonicalFinding) -> dict:
    title_lower = finding.title.lower()
    desc_lower = finding.description.lower()
    combined = f"{title_lower} {desc_lower}"

    if "strict-transport-security" in combined or "hsts" in combined:
        steps = _steps(
            (
                "Locate your web server or CDN config",
                "Identify where HTTP response headers are set (nginx, Apache, Cloudflare, AWS ALB, etc.).",
                "You can find the active server in response headers or your deployment docs.",
            ),
            (
                "Add the HSTS header",
                "Set `Strict-Transport-Security: max-age=31536000; includeSubDomains` on all HTTPS responses.",
                "Use browser devtools → Network → select document → confirm header is present.",
            ),
            (
                "Enforce HTTPS redirects",
                "Redirect all HTTP traffic to HTTPS before applying HSTS in production.",
                "Visit `http://` version of the site; it should redirect to `https://`.",
            ),
            (
                "Rescan to verify",
                "Run a new ComplianceGuard scan against the same target after deploy.",
                "The HSTS finding should clear or severity should drop on the next scan.",
            ),
        )
        summary = "Enable HTTP Strict Transport Security (HSTS) to prevent downgrade attacks."
    elif "content-security-policy" in combined or "csp" in combined:
        steps = _steps(
            (
                "Inventory required script/style sources",
                "List all domains your app loads scripts, styles, fonts, and images from.",
                "Review page source and network tab for third-party domains.",
            ),
            (
                "Deploy a restrictive CSP",
                "Start with `Content-Security-Policy: default-src 'self';` and loosen only as needed.",
                "Check browser console for CSP violation reports after deploy.",
            ),
            (
                "Use report-only mode first (optional)",
                "Test with `Content-Security-Policy-Report-Only` before enforcing.",
                "Monitor reports for blocked resources before switching to enforce mode.",
            ),
            (
                "Rescan to verify",
                "Re-run the scan after headers are live in production.",
                "Confirm the CSP finding no longer appears.",
            ),
        )
        summary = "Define a Content Security Policy to reduce XSS and data injection impact."
    elif "cookie" in combined and ("secure" in combined or "httponly" in combined):
        steps = _steps(
            (
                "Find session cookie configuration",
                "Locate where session/auth cookies are set in your app framework or API gateway.",
                "Inspect `Set-Cookie` in the login response.",
            ),
            (
                "Set Secure and HttpOnly flags",
                "Add `Secure; HttpOnly; SameSite=Lax` (or Strict) to session cookies.",
                "`document.cookie` should not expose the session cookie in browser console.",
            ),
            (
                "Rotate sessions after change",
                "Invalidate existing sessions so users receive new cookie attributes.",
                "Log out and log in; verify new `Set-Cookie` attributes.",
            ),
            (
                "Rescan to verify",
                "Run another scan on the authenticated flow if cookies appear on login.",
                "Cookie-related findings should be resolved.",
            ),
        )
        summary = "Harden session cookies with Secure and HttpOnly attributes."
    elif "sql injection" in combined or "sqli" in combined or finding.cwe_id == "CWE-89":
        steps = _steps(
            (
                "Identify the vulnerable parameter",
                "Review the affected URL or form named in the finding and evidence.",
                "Map user input that reaches the database query.",
            ),
            (
                "Use parameterized queries",
                "Replace string concatenation with prepared statements / ORM bindings.",
                "Code review shows no raw user input in SQL strings.",
            ),
            (
                "Add input validation",
                "Validate and allow-list expected input types and lengths at the API layer.",
                "Fuzz testing no longer produces SQL errors in responses.",
            ),
            (
                "Rescan in authorized lab only",
                "Retest only on systems you own or have written permission to test.",
                "SQLi finding should not reproduce on rescan.",
            ),
        )
        summary = "Eliminate SQL injection by parameterizing queries and validating input."
    elif "xss" in combined or "cross-site" in combined or finding.cwe_id == "CWE-79":
        steps = _steps(
            (
                "Locate the output context",
                "Determine where untrusted input is rendered (HTML, attribute, JS, URL).",
                "Match finding evidence to template or API field.",
            ),
            (
                "Encode output contextually",
                "Use framework auto-escaping or context-specific encoding (HTML, JS, URL).",
                "Inject test payloads; they should display as text, not execute.",
            ),
            (
                "Deploy CSP as defense in depth",
                "Add a Content-Security-Policy that restricts inline scripts.",
                "Browser blocks inline script execution in tests.",
            ),
            (
                "Rescan to verify",
                "Run a follow-up scan after fixes are deployed.",
                "XSS finding should no longer appear.",
            ),
        )
        summary = "Fix XSS by encoding output and reducing inline script usage."
    else:
        steps = _steps(
            (
                "Understand the risk",
                f"Review the finding: {finding.title}. Severity: {finding.severity}.",
                "Document business impact and affected asset owners.",
            ),
            (
                "Apply vendor or framework guidance",
                finding.remediation
                or "Follow OWASP, vendor advisories, or CIS benchmarks for this control.",
                "Configuration or patch matches recommended baseline.",
            ),
            (
                "Test in staging first",
                "Apply the fix in a non-production environment when possible.",
                "Staging rescan or manual test shows issue addressed.",
            ),
            (
                "Deploy and rescan",
                "Promote the fix to production and run a new ComplianceGuard scan.",
                "Finding is closed or downgraded on the next assessment.",
            ),
        )
        summary = finding.remediation or f"Remediate {finding.title} following security best practices."

    priority = {
        "critical": "immediate",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "low",
    }.get(finding.severity.lower(), "medium")

    return {
        "summary": summary,
        "priority": priority,
        "estimated_effort": "30 minutes – 2 hours" if priority in ("immediate", "high") else "1 – 4 hours",
        "steps": steps,
        "compliance_notes": (
            "Addressing this finding improves alignment with OWASP, PCI-DSS, and HIPAA "
            "technical control expectations. Map to your internal change-management process."
        ),
        "confidence": 0.75,
        "powered_by_ai": False,
    }
