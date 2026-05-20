"""OWASP ZAP scanner adapter with policy restrictions."""

import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.scanners.base import BaseScannerAdapter, ScanResult


class ZapScannerAdapter(BaseScannerAdapter):
    scanner_type = "zap"

    async def scan(self, target: str, options: dict[str, Any] | None = None) -> ScanResult:
        start = time.monotonic()
        target = self.sanitize_target(target)

        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"

        settings = get_settings()
        zap_url = settings.zap_api_url.rstrip("/")
        api_key = options.get("api_key", "") if options else ""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"apikey": api_key} if api_key else {}

                spider_resp = await client.get(
                    f"{zap_url}/JSON/spider/action/scan/",
                    params={**params, "url": target, "maxChildren": "10"},
                )
                spider_data = spider_resp.json()
                scan_id = spider_data.get("scan", "")

                if not scan_id:
                    return ScanResult(
                        scanner=self.scanner_type,
                        success=False,
                        error="Failed to start ZAP spider",
                        duration_seconds=time.monotonic() - start,
                    )

                for _ in range(60):
                    status_resp = await client.get(
                        f"{zap_url}/JSON/spider/view/status/",
                        params={**params, "scanId": scan_id},
                    )
                    status = int(status_resp.json().get("status", "100"))
                    if status >= 100:
                        break
                    await self._wait(5)

                ascan_resp = await client.get(
                    f"{zap_url}/JSON/ascan/action/scan/",
                    params={
                        **params,
                        "url": target,
                        "recurse": "false",
                        "inScopeOnly": "true",
                        "scanPolicyName": "Low",
                    },
                )
                ascan_id = ascan_resp.json().get("scan", "")

                if ascan_id:
                    for _ in range(120):
                        ascan_status = await client.get(
                            f"{zap_url}/JSON/ascan/view/status/",
                            params={**params, "scanId": ascan_id},
                        )
                        if int(ascan_status.json().get("status", "100")) >= 100:
                            break
                        await self._wait(10)

                alerts_resp = await client.get(
                    f"{zap_url}/JSON/core/view/alerts/",
                    params={**params, "baseurl": target},
                )
                alerts = alerts_resp.json().get("alerts", [])
                findings = self._parse_alerts(alerts, target)

                return ScanResult(
                    scanner=self.scanner_type,
                    success=True,
                    findings=findings,
                    duration_seconds=time.monotonic() - start,
                )
        except Exception as exc:
            return ScanResult(
                scanner=self.scanner_type,
                success=False,
                error=str(exc)[:1000],
                duration_seconds=time.monotonic() - start,
            )

    async def _wait(self, seconds: int) -> None:
        import asyncio
        await asyncio.sleep(seconds)

    def _parse_alerts(self, alerts: list[dict], target: str) -> list[dict[str, Any]]:
        risk_map = {"High": "high", "Medium": "medium", "Low": "low", "Informational": "info"}
        findings = []
        for alert in alerts:
            risk = alert.get("risk", "Informational")
            findings.append({
                "scanner": self.scanner_type,
                "category": alert.get("pluginId", "web"),
                "severity": risk_map.get(risk, "info"),
                "title": alert.get("name", "ZAP Alert")[:500],
                "description": alert.get("desc", "")[:5000],
                "affected_asset": alert.get("url", target),
                "evidence": alert.get("evidence", ""),
                "remediation": alert.get("solution", ""),
                "references": [alert.get("reference", "")] if alert.get("reference") else [],
                "cwe": alert.get("cweid"),
                "raw_data": alert,
            })
        return findings
