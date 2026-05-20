"""Cryptographic utilities and password handling."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(
    subject: str,
    organization_id: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": organization_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "iss": settings.jwt_issuer,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, token_family: str) -> tuple[str, str]:
    settings = get_settings()
    jti = secrets.token_urlsafe(32)
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "iss": settings.jwt_issuer,
        "type": "refresh",
        "jti": jti,
        "family": token_family,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )


def verify_token(token: str, expected_type: str) -> dict[str, Any] | None:
    try:
        payload = decode_token(token)
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def generate_token_family() -> str:
    return secrets.token_urlsafe(32)


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


class FieldEncryptor:
    def __init__(self, key: str) -> None:
        if not key:
            self._fernet: Fernet | None = None
        else:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, value: str) -> str:
        if not self._fernet:
            raise ValueError("Field encryption key not configured")
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        if not self._fernet:
            raise ValueError("Field encryption key not configured")
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt field") from exc


def get_field_encryptor() -> FieldEncryptor:
    return FieldEncryptor(get_settings().field_encryption_key)


def sign_internal_request(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_internal_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = sign_internal_request(payload, secret)
    return constant_time_compare(expected, signature)
