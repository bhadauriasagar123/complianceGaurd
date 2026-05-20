"""Domain enumerations."""

from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "organization_admin"
    SECURITY_ANALYST = "security_analyst"
    AUDITOR = "auditor"
    READ_ONLY = "read_only_viewer"


class ScanStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    QUEUED = "queued"
    RUNNING = "running"
    NORMALIZING = "normalizing"
    AI_PROCESSING = "ai_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    WEB_APPLICATION = "web_application"
    API = "api"
    CONTAINER = "container"
    FULL_ASSESSMENT = "full_assessment"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScannerType(StrEnum):
    NMAP = "nmap"
    NUCLEI = "nuclei"
    ZAP = "zap"
    TRIVY = "trivy"
    SEMGREP = "semgrep"
    BANDIT = "bandit"
    GITLEAKS = "gitleaks"


class ComplianceFramework(StrEnum):
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    OWASP_TOP_10 = "owasp_top_10"


class AuditAction(StrEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    PASSWORD_RESET = "password_reset"
    SCAN_CREATED = "scan_created"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    SCAN_CANCELLED = "scan_cancelled"
    TARGET_AUTHORIZED = "target_authorized"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    REPORT_GENERATED = "report_generated"
    SETTINGS_UPDATED = "settings_updated"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    UserRole.SUPER_ADMIN: {
        "org:read", "org:write", "org:delete",
        "user:read", "user:write", "user:delete",
        "scan:read", "scan:write", "scan:delete", "scan:execute",
        "finding:read", "finding:write",
        "report:read", "report:write",
        "audit:read",
        "target:read", "target:write", "target:delete",
        "compliance:read", "compliance:write",
        "settings:read", "settings:write",
        "system:admin",
    },
    UserRole.ORG_ADMIN: {
        "org:read", "org:write",
        "user:read", "user:write", "user:delete",
        "scan:read", "scan:write", "scan:delete", "scan:execute",
        "finding:read", "finding:write",
        "report:read", "report:write",
        "audit:read",
        "target:read", "target:write", "target:delete",
        "compliance:read", "compliance:write",
        "settings:read", "settings:write",
    },
    UserRole.SECURITY_ANALYST: {
        "org:read",
        "user:read",
        "scan:read", "scan:write", "scan:execute",
        "finding:read", "finding:write",
        "report:read", "report:write",
        "target:read", "target:write",
        "compliance:read",
    },
    UserRole.AUDITOR: {
        "org:read",
        "user:read",
        "scan:read",
        "finding:read",
        "report:read",
        "audit:read",
        "target:read",
        "compliance:read",
    },
    UserRole.READ_ONLY: {
        "org:read",
        "scan:read",
        "finding:read",
        "report:read",
        "compliance:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms
