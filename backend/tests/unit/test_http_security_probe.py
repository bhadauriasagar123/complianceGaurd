"""Tests for passive HTTP security probe."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scanners.http_security_probe import HttpSecurityProbeAdapter


def _mock_response(
    *,
    status_code: int = 200,
    url: str = "https://example.com/",
    headers: dict | None = None,
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.headers = headers or {"Server": "nginx/1.18"}
    return resp


@pytest.mark.asyncio
async def test_probe_reports_missing_security_headers():
    adapter = HttpSecurityProbeAdapter()
    mock_resp = _mock_response(headers={"Server": "nginx"})

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.scanners.http_security_probe.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.scan("https://example.com")

    assert result.success
    titles = [f["title"] for f in result.findings]
    assert any("HSTS" in t for t in titles)
    assert any("CSP" in t for t in titles)


@pytest.mark.asyncio
async def test_probe_reports_server_disclosure():
    adapter = HttpSecurityProbeAdapter()
    mock_resp = _mock_response(
        headers={
            "Server": "Apache/2.4",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        }
    )

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.scanners.http_security_probe.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.scan("https://example.com")

    assert result.success
    assert any("Server information disclosed" in f["title"] for f in result.findings)
