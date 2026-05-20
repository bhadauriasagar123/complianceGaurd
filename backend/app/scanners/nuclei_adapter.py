"""Nuclei scanner adapter with template whitelisting."""

import json
import os
import tempfile
import time
from typing import Any

from app.core.config import get_settings
from app.scanners.base import BaseScannerAdapter, ScanResult

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}


class NucleiScannerAdapter(BaseScannerAdapter):
    scanner_type = "nuclei"

    async def scan(self, target: str, options: dict[str, Any] | None = None) -> ScanResult:
        start = time.monotonic()
        target = self.sanitize_target(target)
        settings = get_settings()

        output_file = os.path.join(tempfile.gettempdir(), f"nuclei_{int(time.time())}.json")
        cmd = [
            settings.nuclei_path,
            "-u", target,
            "-jsonl",
            "-o", output_file,
            "-severity", "critical,high,medium,low",
            "-timeout", "10",
            "-rate-limit", "50",
            "-bulk-size", "10",
            "-templates", settings.nuclei_templates_path,
            "-disable-update-check",
        ]

        try:
            returncode, stdout, stderr = await self.run_subprocess(cmd, timeout=1800)
            findings = self._parse_jsonl(output_file, target)

            return ScanResult(
                scanner=self.scanner_type,
                success=True,
                findings=findings,
                raw_output=stdout,
                error=stderr[:500] if stderr and returncode != 0 else None,
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:
            return ScanResult(
                scanner=self.scanner_type,
                success=False,
                error=str(exc)[:1000],
                duration_seconds=time.monotonic() - start,
            )

    def _parse_jsonl(self, output_file: str, target: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        try:
            with open(output_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    info = data.get("info", {})
                    severity = info.get("severity", "info").lower()
                    if severity not in ALLOWED_SEVERITIES:
                        severity = "info"

                    findings.append({
                        "scanner": self.scanner_type,
                        "category": info.get("classification", {}).get("cve-id", ["general"])[0] if isinstance(info.get("classification"), dict) else "web",
                        "severity": severity,
                        "title": info.get("name", data.get("template-id", "Unknown"))[:500],
                        "description": info.get("description", "")[:5000],
                        "affected_asset": data.get("host", target),
                        "evidence": data.get("matcher-name", ""),
                        "remediation": info.get("remediation", ""),
                        "references": info.get("reference", []),
                        "cwe": (info.get("classification", {}) or {}).get("cwe-id", [None])[0] if isinstance(info.get("classification"), dict) else None,
                        "cve": (info.get("classification", {}) or {}).get("cve-id", [None])[0] if isinstance(info.get("classification"), dict) else None,
                        "raw_data": data,
                    })
        except FileNotFoundError:
            pass
        return findings
