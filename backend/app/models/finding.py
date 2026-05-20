"""Finding model - canonical vulnerability record."""

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import PortableJSON


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "findings"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_asset: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    references_json: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    compliance_mappings: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    exploitability: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cwe_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cve_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_data: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_remediation: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")
