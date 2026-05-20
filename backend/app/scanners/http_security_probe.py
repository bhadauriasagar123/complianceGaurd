"""Passive HTTP security checks — no scanner binaries required (works on Render free tier)."""

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.scanners.base import BaseScannerAdapter, ScanResult
from app.services.target_validation import TargetValidationError, TargetValidator

REQUIRED_HEADERS: dict[str, dict[str, str]] = {
    "strict-transport-security": {
        "severity": "medium",
        "title": "Missing Strict-Transport-Security (HSTS)",
        "description": "HSTS was not set. Browsers may allow downgrade to HTTP.",
        "remediation": "Add Strict-Transport-Security: max-age=31536000; includeSubDomains",
        "cwe": "CWE-319",
    },
    "content-security-policy": {
        "severity": "medium",
        "title": "Missing Content-Security-Policy (CSP)",
        "description": "No CSP header detected. Increases XSS impact.",
        "remediation": "Define a restrictive Content-Security-Policy for the application.",
        "cwe": "CWE-1021",
    },
    "x-content-type-options": {
        "severity": "low",
        "title": "Missing X-Content-Type-Options",
        "description": "nosniff is not enforced; MIME confusion attacks are easier.",
        "remediation": "Set X-Content-Type-Options: nosniff",
        "cwe": "CWE-693",
    },
    "x-frame-options": {
        "severity": "low",
        "title": "Missing X-Frame-Options / frame-ancestors",
        "description": "Clickjacking protections were not detected.",
        "remediation": "Set X-Frame-Options: DENY or CSP frame-ancestors 'none'",
        "cwe": "CWE-1021",
    },
    "referrer-policy": {
        "severity": "info",
        "title": "Missing Referrer-Policy",
        "description": "Referrer leakage to third parties may occur.",
        "remediation": "Set Referrer-Policy: strict-origin-when-cross-origin",
        "cwe": "CWE-200",
    },
}

DISCLOSURE_HEADERS = ("server", "x-powered-by", "x-aspnet-version", "x-generator")


class HttpSecurityProbeAdapter(BaseScannerAdapter):
    scanner_type = "http_probe"

    async def scan(self, target: str, options: dict[str, Any] | None = None) -> ScanResult:
        start = time.monotonic()
        target = self.sanitize_target(target)
        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"

        validator = TargetValidator()
        try:
            validator.validate(target, "url")
        except TargetValidationError as exc:
            return ScanResult(
                scanner=self.scanner_type,
                success=False,
                error=exc.message,
                duration_seconds=time.monotonic() - start,
            )

        findings: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(8.0, connect=4.0),
                limits=httpx.Limits(max_connections=2),
                max_redirects=5,
                headers={"User-Agent": "ComplianceGuard-SecurityProbe/1.0"},
            ) as client:
                response = await client.get(target)
                findings.extend(self._analyze_response(target, response))
        except httpx.HTTPError as exc:
            return ScanResult(
                scanner=self.scanner_type,
                success=False,
                error=f"HTTP probe failed: {exc}"[:1000],
                duration_seconds=time.monotonic() - start,
            )

        return ScanResult(
            scanner=self.scanner_type,
            success=True,
            findings=findings,
            duration_seconds=time.monotonic() - start,
        )

    def _analyze_response(self, target: str, response: httpx.Response) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        host = urlparse(target).netloc

        if target.startswith("http://") and response.url.scheme == "http":
            findings.append({
                "scanner": self.scanner_type,
                "category": "transport",
                "severity": "high",
                "title": "Site served over cleartext HTTP",
                "description": "Target did not redirect to HTTPS. Credentials and session data may be exposed.",
                "affected_asset": target,
                "evidence": f"Final URL: {response.url}",
                "remediation": "Enforce HTTPS redirects and HSTS.",
                "cwe": "CWE-319",
            })

        for header_name, meta in REQUIRED_HEADERS.items():
            if header_name not in headers_lower:
                findings.append({
                    "scanner": self.scanner_type,
                    "category": "security_headers",
                    "severity": meta["severity"],
                    "title": meta["title"],
                    "description": meta["description"],
                    "affected_asset": host,
                    "evidence": f"Response {response.status_code} from {response.url}",
                    "remediation": meta["remediation"],
                    "cwe": meta["cwe"],
                })

        for disclosure in DISCLOSURE_HEADERS:
            if disclosure in headers_lower:
                findings.append({
                    "scanner": self.scanner_type,
                    "category": "information_disclosure",
                    "severity": "low",
                    "title": f"Server information disclosed ({disclosure})",
                    "description": f"The {disclosure} header reveals stack or product details.",
                    "affected_asset": host,
                    "evidence": f"{disclosure}: {headers_lower[disclosure][:200]}",
                    "remediation": "Remove or genericize version headers in reverse proxy / web server config.",
                    "cwe": "CWE-200",
                })

        set_cookie = headers_lower.get("set-cookie", "")
        if set_cookie and "secure" not in set_cookie.lower():
            findings.append({
                "scanner": self.scanner_type,
                "category": "session",
                "severity": "medium",
                "title": "Cookie missing Secure flag",
                "description": "Set-Cookie was observed without the Secure attribute.",
                "affected_asset": host,
                "evidence": set_cookie[:300],
                "remediation": "Set Secure and HttpOnly on session cookies.",
                "cwe": "CWE-614",
            })
        if set_cookie and "httponly" not in set_cookie.lower():
            findings.append({
                "scanner": self.scanner_type,
                "category": "session",
                "severity": "medium",
                "title": "Cookie missing HttpOnly flag",
                "description": "Session cookies may be readable from JavaScript (XSS risk).",
                "affected_asset": host,
                "evidence": set_cookie[:300],
                "remediation": "Set HttpOnly on session cookies.",
                "cwe": "CWE-1004",
            })

        if response.status_code >= 500:
            findings.append({
                "scanner": self.scanner_type,
                "category": "availability",
                "severity": "info",
                "title": f"Server error response ({response.status_code})",
                "description": "The server returned an error status; may indicate misconfiguration.",
                "affected_asset": str(response.url),
                "evidence": f"HTTP {response.status_code}",
            })

        return findings
