"""Authentication schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{12,}$"
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    organization_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 12 characters with uppercase, lowercase, digit, and special character"
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)
    organization_slug: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError("Password does not meet complexity requirements")
        return v


class EmailVerifyRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_verified: bool
    mfa_enabled: bool
    role: str
    organization_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: UUID
    device_name: str | None
    ip_address: str | None
    last_activity_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
