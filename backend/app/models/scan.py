"""Scan and scan job models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import PortableJSON


class Scan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scans"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    authorized_target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authorized_targets.id"), nullable=False
    )
    target_value: Mapped[str] = mapped_column(String(500), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    scanners_enabled: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=list)
    consent_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    consent_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_phase: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    organization = relationship("Organization", back_populates="scans")
    jobs = relationship("ScanJob", back_populates="scan", lazy="selectin")
    findings = relationship("Finding", back_populates="scan", lazy="noload")


class ScanJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scan_jobs"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    scan = relationship("Scan", back_populates="jobs")
