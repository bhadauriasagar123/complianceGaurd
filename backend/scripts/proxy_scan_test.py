"""Test scan create via Vite proxy (:5173)."""
import asyncio
import uuid

import httpx


async def main() -> None:
    email = f"proxy-{uuid.uuid4().hex[:8]}@example.com"
    org_name = f"Proxy Org {uuid.uuid4().hex[:6]}"
    async with httpx.AsyncClient(base_url="http://127.0.0.1:5173", timeout=60) as c:
        h = await c.get("/health")
        csrf = h.cookies.get("cg_csrf_token") or ""
        headers = {"X-CSRF-Token": csrf}
        reg = await c.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ssw0rd!99",
                "full_name": "Proxy User",
                "organization_name": org_name,
            },
            headers=headers,
        )
        print("reg", reg.status_code, reg.text[:200])
        if reg.status_code != 201:
            return
        await asyncio.sleep(0.3)
        login = await c.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ssw0rd!99"},
            headers=headers,
        )
        print("login", login.status_code)
        if login.status_code != 200:
            print(login.text[:200])
            return
        headers["Authorization"] = f"Bearer {login.json()['access_token']}"
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
        print("tgt", tgt.status_code)
        if tgt.status_code != 201:
            print(tgt.text[:200])
            return
        tid = tgt.json()["id"]
        await asyncio.sleep(0.3)
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
        print("scan", scan.status_code, scan.text[:500])


if __name__ == "__main__":
    asyncio.run(main())
