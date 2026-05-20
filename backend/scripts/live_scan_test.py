"""Test scan create against live API on :8000."""
import asyncio
import uuid

import httpx


async def main() -> None:
    email = f"live-{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60) as c:
        h = await c.get("/health")
        csrf = h.cookies.get("cg_csrf_token") or ""
        headers = {"X-CSRF-Token": csrf}
        reg = await c.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ssw0rd!99",
                "full_name": "Live User",
                "organization_name": "L Org",
            },
            headers=headers,
        )
        print("reg", reg.status_code, reg.text[:200])
        if reg.status_code != 201:
            return
        login = await c.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ssw0rd!99"},
            headers=headers,
        )
        print("login", login.status_code)
        token = login.json()["access_token"]
        headers["Authorization"] = f"Bearer {token}"
        tgt = await c.post(
            "/api/v1/targets",
            json={
                "target_value": "https://example.com",
                "target_type": "url",
                "verification_method": "dns",
                "consent_confirmed": True,
            },
            headers=headers,
        )
        print("tgt", tgt.status_code)
        tid = tgt.json()["id"]
        scan = await c.post(
            "/api/v1/scans",
            json={
                "authorized_target_id": tid,
                "scan_type": "web_application",
                "scanners_enabled": ["nmap"],
                "consent_confirmed": True,
            },
            headers=headers,
        )
        print("scan", scan.status_code, scan.text[:400])


if __name__ == "__main__":
    asyncio.run(main())
