"""Scan job enqueue with Celery fallback for local dev without Redis."""

import asyncio
import logging

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.workers.tasks import _orchestrate_scan, orchestrate_scan

logger = logging.getLogger(__name__)


async def _run_orchestration_inline(scan_id: str) -> None:
    """Run scan pipeline in-process (dev fallback when Redis/Celery unavailable)."""
    logger.info("inline_scan_orchestration_start", scan_id=scan_id)
    # Brief delay so the API request can commit before we write to SQLite
    await asyncio.sleep(1.0)
    try:
        await _orchestrate_scan(scan_id)
        logger.info("inline_scan_orchestration_done", scan_id=scan_id)
    except Exception as exc:
        logger.exception("inline_scan_orchestration_failed", scan_id=scan_id, error=str(exc))


def enqueue_scan(scan_id: str, background_tasks: BackgroundTasks) -> str:
    """
    Queue scan orchestration. Returns mode used: 'celery' or 'background'.
    In development, runs in-process when Redis is unavailable (no Docker required).
    """
    settings = get_settings()

    if settings.app_env == "development" or settings.scan_dev_mock:
        background_tasks.add_task(_run_orchestration_inline, scan_id)
        return "background"

    if _celery_available():
        try:
            orchestrate_scan.delay(scan_id)
            return "celery"
        except Exception as exc:
            logger.warning("celery_enqueue_failed", scan_id=scan_id, error=str(exc))

    background_tasks.add_task(_run_orchestration_inline, scan_id)
    logger.info("scan_enqueued_inline", scan_id=scan_id)
    return "background"


def _celery_available() -> bool:
    try:
        from app.workers.celery_app import celery_app

        celery_app.connection().ensure_connection(max_retries=1, timeout=1)
        return True
    except Exception:
        return False
