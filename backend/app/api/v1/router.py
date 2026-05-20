"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import audit, auth, reports, scans, websocket

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(scans.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
api_router.include_router(websocket.router)
