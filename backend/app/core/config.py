"""Application configuration with secure defaults."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ComplianceGuard"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    api_version: str = "v1"
    secret_key: str = Field(min_length=32)

    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "complianceguard"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str = "localhost"

    field_encryption_key: str = ""

    mfa_issuer: str = "ComplianceGuard"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@complianceguard.io"
    smtp_tls: bool = True

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.1

    scan_max_concurrent: int = 5
    scan_timeout_seconds: int = 3600
    scan_rate_limit_per_hour: int = 10
    scan_deny_private_ips: bool = True
    scan_deny_localhost: bool = True
    scan_deny_metadata: bool = True
    scan_sandbox_network: str = "scan-sandbox"

    nmap_path: str = "/usr/bin/nmap"
    nuclei_path: str = "/usr/bin/nuclei"
    nuclei_templates_path: str = "/opt/nuclei-templates"
    zap_api_url: str = "http://zap:8080"

    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    log_level: str = "INFO"
    prometheus_enabled: bool = True

    vault_addr: str = ""
    vault_token: str = ""
    vault_mount: str = "secret"

    max_upload_size_mb: int = 10
    allowed_upload_mimes: str = "application/pdf,image/png,image/jpeg"

    report_storage_path: str = "/app/reports"
    report_retention_days: int = 90

    # Free-tier / demo hosting: run scans without Redis, Celery, or scanner binaries
    scan_mock_mode: bool = False

    @field_validator("app_debug")
    @classmethod
    def disable_debug_in_production(cls, v: bool, info) -> bool:
        if info.data.get("app_env") == "production" and v:
            return False
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def scan_dev_mock(self) -> bool:
        """Fast in-process scan path for local SQLite (avoids long DB locks)."""
        return self.app_env == "development" and self.is_sqlite

    @property
    def use_scan_mock(self) -> bool:
        """Use lightweight mock scan pipeline (no Nmap/Nuclei/ZAP/Redis required)."""
        return self.scan_mock_mode or self.scan_dev_mock

    @property
    def allowed_upload_mimes_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_upload_mimes.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
