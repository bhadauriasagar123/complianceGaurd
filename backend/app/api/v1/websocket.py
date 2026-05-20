"""WebSocket for live scan progress."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import verify_token
from app.models.scan import Scan

router = APIRouter()


@router.websocket("/ws/scans/{scan_id}")
async def scan_progress_ws(websocket: WebSocket, scan_id: str) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    payload = verify_token(token, "access")
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    org_id = UUID(payload["org_id"])
    await websocket.accept()

    try:
        while True:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Scan).where(
                        Scan.id == UUID(scan_id),
                        Scan.organization_id == org_id,
                    )
                )
                scan = result.scalar_one_or_none()

                if scan:
                    await websocket.send_json({
                        "scan_id": str(scan.id),
                        "status": scan.status,
                        "progress_percent": scan.progress_percent,
                        "current_phase": scan.current_phase,
                        "compliance_score": scan.compliance_score,
                    })
                    if scan.status in ("completed", "failed", "cancelled"):
                        break

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
