"""Nmap scanner adapter with XML parsing."""

import os
import tempfile
import time
from typing import Any

from defusedxml.ElementTree import fromstring

from app.core.config import get_settings
from app.scanners.base import BaseScannerAdapter, ScanResult


class NmapScannerAdapter(BaseScannerAdapter):
    scanner_type = "nmap"

    async def scan(self, target: str, options: dict[str, Any] | None = None) -> ScanResult:
        start = time.monotonic()
        target = self.sanitize_target(target)
        settings = get_settings()

        host = target
        if target.startswith("http"):
            from urllib.parse import urlparse
            host = urlparse(target).hostname or target

        output_file = os.path.join(tempfile.gettempdir(), f"nmap_{int(time.time())}.xml")
        cmd = [
            settings.nmap_path,
            "-sV",
            "-sC",
            "--script", "vulners",
            "-oX", output_file,
            "-T4",
            "--max-retries", "2",
            "--host-timeout", "300s",
            host,
        ]

        try:
            returncode, stdout, stderr = await self.run_subprocess(cmd, timeout=600)
            findings = []

            try:
                with open(output_file, encoding="utf-8") as f:
                    xml_content = f.read()
                findings = self._parse_nmap_xml(xml_content, host)
            except FileNotFoundError:
                if stderr:
                    return ScanResult(
                        scanner=self.scanner_type,
                        success=False,
                        error=stderr[:1000],
                        duration_seconds=time.monotonic() - start,
                    )

            return ScanResult(
                scanner=self.scanner_type,
                success=returncode == 0 or len(findings) > 0,
                findings=findings,
                raw_output=stdout,
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:
            return ScanResult(
                scanner=self.scanner_type,
                success=False,
                error=str(exc)[:1000],
                duration_seconds=time.monotonic() - start,
            )

    def _parse_nmap_xml(self, xml_content: str, host: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        root = fromstring(xml_content)

        for host_elem in root.findall("host"):
            for port in host_elem.findall(".//port"):
                portid = port.get("portid", "")
                protocol = port.get("protocol", "tcp")
                state = port.find("state")
                if state is not None and state.get("state") != "open":
                    continue

                service = port.find("service")
                service_name = service.get("name", "unknown") if service is not None else "unknown"
                version = service.get("version", "") if service is not None else ""

                findings.append({
                    "scanner": self.scanner_type,
                    "category": "service_discovery",
                    "severity": "info",
                    "title": f"Open port {portid}/{protocol} - {service_name}",
                    "description": f"Service {service_name} {version} detected on port {portid}",
                    "affected_asset": f"{host}:{portid}",
                    "evidence": f"Protocol: {protocol}, Service: {service_name}, Version: {version}",
                })

                for script in port.findall(".//script"):
                    if script.get("id") == "vulners":
                        for table in script.findall("table"):
                            for elem in table.findall("elem"):
                                if elem.get("key") == "cvss":
                                    cvss = float(elem.text or "0")
                                    severity = "critical" if cvss >= 9 else "high" if cvss >= 7 else "medium" if cvss >= 4 else "low"
                                    cve_elem = table.find(".//elem[@key='id']")
                                    cve_id = cve_elem.text if cve_elem is not None else None
                                    findings.append({
                                        "scanner": self.scanner_type,
                                        "category": "vulnerability",
                                        "severity": severity,
                                        "title": f"CVE {cve_id} on port {portid}" if cve_id else f"Vulnerability on port {portid}",
                                        "description": f"Vulners detection with CVSS {cvss}",
                                        "affected_asset": f"{host}:{portid}",
                                        "cvss": cvss,
                                        "cve": cve_id,
                                    })

        return findings
