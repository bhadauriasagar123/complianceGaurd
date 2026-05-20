"""Scan-related schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import ScannerType, ScanType


class AuthorizedTargetCreate(BaseModel):
    target_value: str = Field(min_length=3, max_length=500)
    target_type: str = Field(pattern=r"^(url|domain|ip|cidr)$")
    ownership_proof: str | None = Field(default=None, max_length=2000)
    verification_method: str = Field(min_length=3, max_length=100)
    consent_confirmed: bool
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("consent_confirmed")
    @classmethod
    def must_confirm_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Explicit consent confirmation is required")
        return v


class AuthorizedTargetResponse(BaseModel):
    id: UUID
    target_value: str
    target_type: str
    normalized_target: str
    is_active: bool
    verification_method: str
    consent_recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanCreateRequest(BaseModel):
    authorized_target_id: UUID
    scan_type: ScanType
    scanners_enabled: list[ScannerType] = Field(min_length=1)
    consent_confirmed: bool

    @field_validator("consent_confirmed")
    @classmethod
    def must_confirm_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Scan consent must be explicitly confirmed")
        return v


class ScanResponse(BaseModel):
    id: UUID
    target_value: str
    scan_type: str
    status: str
    progress_percent: int
    current_phase: str | None
    scanners_enabled: list
    compliance_score: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    error_message: str | None

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: UUID
    scanner: str
    category: str
    severity: str
    cvss_score: float | None
    title: str
    description: str
    affected_asset: str
    evidence: str | None
    remediation: str | None
    compliance_mappings: dict | None
    cwe_id: str | None
    cve_id: str | None
    ai_remediation: str | None
    ai_confidence: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanListResponse(BaseModel):
    items: list[ScanResponse]
    total: int
    page: int
    page_size: int
