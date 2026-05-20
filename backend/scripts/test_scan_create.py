"""Test full API scan create with exception details."""
import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as c:
        h = await c.get("/health")
        c.headers["X-CSRF-Token"] = h.cookies.get("cg_csrf_token", "x")

        email = "apitest@example.com"
        reg = await c.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ssw0rd!99",
                "full_name": "API Test",
                "organization_name": "API Org",
            },
        )
        if reg.status_code == 201:
            login = await c.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "SecureP@ssw0rd!99"},
            )
        else:
            login = await c.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "SecureP@ssw0rd!99"},
            )
        print("login", login.status_code)
        c.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        tgt = await c.post(
            "/api/v1/targets",
            json={
                "target_value": "https://admin.hostexam.net/account?returnUrl=%2Fdashboard%2Fstatistics",
                "target_type": "url",
                "verification_method": "dns_txt_record",
                "consent_confirmed": True,
            },
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
        )
        print("scan", scan.status_code, scan.text[:800])


if __name__ == "__main__":
    asyncio.run(main())
