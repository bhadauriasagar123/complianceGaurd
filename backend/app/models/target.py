"""Authorized target model for scan authorization."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AuthorizedTarget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "authorized_targets"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    target_value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    normalized_target: Mapped[str] = mapped_column(String(500), nullable=False)
    ownership_proof: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consent_recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_method: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="targets")
