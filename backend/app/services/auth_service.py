"""Authentication service."""

import base64
import io
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pyotp
import qrcode
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_token_family,
    get_field_encryptor,
    hash_password,
    hash_token,
    verify_password,
)
from app.domain.enums import AuditAction, UserRole
from app.models.organization import Organization, OrganizationMember
from app.models.session import RefreshToken, UserSession
from app.models.user import User
from app.services.audit_service import AuditService

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:50] or str(uuid4())[:8]


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.audit = AuditService(db)

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
        ip_address: str | None = None,
    ) -> tuple[User, Organization]:
        existing = await self.db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            verification_token_hash=hash_token(secrets.token_urlsafe(32)),
            verification_token_expires=datetime.now(UTC) + timedelta(hours=24),
        )
        self.db.add(user)
        await self.db.flush()

        base_slug = _slugify(organization_name)
        slug = base_slug
        for attempt in range(5):
            existing_org = await self.db.execute(select(Organization).where(Organization.slug == slug))
            if not existing_org.scalar_one_or_none():
                break
            slug = f"{base_slug}-{secrets.token_hex(3)}"
        else:
            raise ValueError("Could not allocate organization slug")

        org = Organization(name=organization_name, slug=slug)
        self.db.add(org)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            raise ValueError("Organization name is already in use") from exc

        membership = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=UserRole.ORG_ADMIN,
        )
        self.db.add(membership)
        await self.db.flush()

        await self.audit.log(
            AuditAction.USER_CREATED,
            organization_id=org.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"email": email},
        )
        # Load server defaults (created_at) before building API response
        await self.db.refresh(user)
        await self.db.refresh(org)
        return user, org

    async def login(
        self,
        email: str,
        password: str,
        mfa_code: str | None,
        organization_slug: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, User, OrganizationMember]:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
                await self.db.flush()
            await self.audit.log(
                AuditAction.LOGIN_FAILED,
                user_id=user.id if user else None,
                ip_address=ip_address,
                outcome="failure",
            )
            raise ValueError("Invalid credentials")

        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise ValueError("Account temporarily locked")

        if user.mfa_enabled:
            if not mfa_code:
                raise ValueError("MFA code required")
            encryptor = get_field_encryptor()
            if not user.mfa_secret_encrypted:
                raise ValueError("MFA not properly configured")
            secret = encryptor.decrypt(user.mfa_secret_encrypted)
            totp = pyotp.TOTP(secret)
            if not totp.verify(mfa_code, valid_window=1):
                await self.audit.log(AuditAction.LOGIN_FAILED, user_id=user.id, outcome="failure", message="Invalid MFA")
                raise ValueError("Invalid MFA code")

        query = (
            select(OrganizationMember)
            .join(Organization)
            .where(OrganizationMember.user_id == user.id, OrganizationMember.is_active == True)  # noqa: E712
        )
        if organization_slug:
            query = query.where(Organization.slug == organization_slug)

        memberships = (await self.db.execute(query)).scalars().all()
        if not memberships:
            raise ValueError("No organization membership found")

        membership = memberships[0]
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        token_family = generate_token_family()
        refresh_token, jti = create_refresh_token(str(user.id), token_family)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            token_family=token_family,
            jti=jti,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )
        self.db.add(refresh_record)

        session = UserSession(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity_at=datetime.now(UTC),
        )
        self.db.add(session)

        access_token = create_access_token(
            str(user.id),
            str(membership.organization_id),
            membership.role,
        )

        await self.audit.log(
            AuditAction.LOGIN,
            organization_id=membership.organization_id,
            user_id=user.id,
            ip_address=ip_address,
        )

        return access_token, refresh_token, user, membership

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        from app.core.security import verify_token

        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise ValueError("Invalid refresh token")

        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if not record or record.expires_at < datetime.now(UTC):
            if record:
                await self._revoke_token_family(record.token_family)
            raise ValueError("Refresh token expired or revoked")

        user_id = UUID(payload["sub"])
        membership_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
        membership = membership_result.scalars().first()
        if not membership:
            raise ValueError("No active membership")

        record.revoked_at = datetime.now(UTC)
        new_refresh, new_jti = create_refresh_token(str(user_id), record.token_family)
        record.replaced_by_jti = new_jti

        new_record = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(new_refresh),
            token_family=record.token_family,
            jti=new_jti,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )
        self.db.add(new_record)

        access_token = create_access_token(
            str(user_id),
            str(membership.organization_id),
            membership.role,
        )
        return access_token, new_refresh

    async def _revoke_token_family(self, family: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_family == family,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in result.scalars().all():
            token.revoked_at = datetime.now(UTC)

    async def setup_mfa(self, user_id: UUID) -> tuple[str, str, str]:
        secret = pyotp.random_base32()
        encryptor = get_field_encryptor()
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.mfa_secret_encrypted = encryptor.encrypt(secret)
        await self.db.flush()

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name=self.settings.mfa_issuer)

        qr = qrcode.make(uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

        return secret, uri, qr_b64

    async def enable_mfa(self, user_id: UUID, code: str) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        encryptor = get_field_encryptor()
        secret = encryptor.decrypt(user.mfa_secret_encrypted or "")
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid MFA code")
        user.mfa_enabled = True
        await self.audit.log(AuditAction.MFA_ENABLED, user_id=user_id)

    async def logout(self, user_id: UUID, refresh_token: str | None = None) -> None:
        if refresh_token:
            token_hash = hash_token(refresh_token)
            result = await self.db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            record = result.scalar_one_or_none()
            if record:
                await self._revoke_token_family(record.token_family)

        sessions = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,  # noqa: E712
            )
        )
        for session in sessions.scalars().all():
            session.is_active = False
            session.revoked_at = datetime.now(UTC)

        await self.audit.log(AuditAction.LOGOUT, user_id=user_id)
