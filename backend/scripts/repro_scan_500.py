"""Reproduce scan 500 against live API."""
import asyncio

import httpx


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as c:
        h = await c.get("/health")
        print("health", h.status_code)
        csrf = h.cookies.get("cg_csrf_token")
        headers = {"X-CSRF-Token": csrf or ""}

        for email in ("repro@example.com",):
            reg = await c.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "SecureP@ssw0rd!99",
                    "full_name": "Repro",
                    "organization_name": "Repro Org",
                },
                headers=headers,
            )
            print("register", reg.status_code, reg.text[:200])
            login = await c.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "SecureP@ssw0rd!99"},
                headers=headers,
            )
            print("login", login.status_code)
            if login.status_code != 200:
                continue
            token = login.json()["access_token"]
            headers["Authorization"] = f"Bearer {token}"

            tgt = await c.post(
                "/api/v1/targets",
                json={
                    "target_value": "https://example.com",
                    "target_type": "url",
                    "verification_method": "dns_txt_record",
                    "consent_confirmed": True,
                },
                headers=headers,
            )
            print("target", tgt.status_code)
            tid = tgt.json()["id"]

            scan = await c.post(
                "/api/v1/scans",
                json={
                    "authorized_target_id": tid,
                    "scan_type": "web_application",
                    "scanners_enabled": ["nmap", "nuclei", "zap"],
                    "consent_confirmed": True,
                },
                headers=headers,
            )
            print("scan", scan.status_code, scan.text)


if __name__ == "__main__":
    asyncio.run(main())
