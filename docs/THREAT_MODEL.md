# ComplianceGuard Threat Model

**Version:** 1.0  
**Date:** 2026-05-20  
**Methodology:** STRIDE

## System Overview

ComplianceGuard is a multi-tenant SaaS platform that performs authorized security assessments against customer-owned infrastructure targets, maps findings to compliance frameworks, and generates remediation guidance via AI.

### Trust Boundaries

```
[Internet] ──▶ [Nginx/WAF] ──▶ [API Layer] ──▶ [Database]
                                  │
                                  ▼
                          [Scan Sandbox] ──▶ [External Targets]
```

## Assets

| Asset | Classification | Impact if Compromised |
|-------|---------------|----------------------|
| User credentials | Confidential | Account takeover |
| Scan findings | Confidential | Exposure of vuln data |
| API keys (Anthropic) | Secret | Financial abuse, data leak |
| Audit logs | Integrity-critical | Compliance violation |
| Customer targets | Operational | Unauthorized scanning |

## Threat Actors

1. **External attacker** — seeks data breach, unauthorized scanning
2. **Malicious tenant** — attempts cross-org access (IDOR)
3. **Compromised account** — insider threat via stolen credentials
4. **Prompt injection attacker** — manipulates AI remediation output
5. **SSRF attacker** — uses scan feature to probe internal networks

## STRIDE Analysis

### Spoofing
| Threat | Mitigation |
|--------|-----------|
| Credential stuffing | Rate limiting, account lockout, MFA |
| Session hijacking | HttpOnly cookies, short-lived JWT, refresh rotation |
| JWT forgery | HS256 with 256-bit secret, issuer validation |

### Tampering
| Threat | Mitigation |
|--------|-----------|
| Audit log modification | Append-only audit_logs, no UPDATE endpoints |
| Finding manipulation | Immutable scan history, org-scoped queries |
| CSRF attacks | Double-submit cookie pattern |

### Repudiation
| Threat | Mitigation |
|--------|-----------|
| Denied scan actions | Audit logs with IP, user agent, trace ID |
| Consent disputes | consent_recorded_at timestamp + user ID |

### Information Disclosure
| Threat | Mitigation |
|--------|-----------|
| Cross-tenant data leak | org_id on all queries, RBAC enforcement |
| Error message leakage | Generic 500 responses in production |
| AI prompt data leak | Input sanitization, no PII in prompts |

### Denial of Service
| Threat | Mitigation |
|--------|-----------|
| Scan flooding | Per-org rate limits, Celery concurrency caps |
| API abuse | SlowAPI rate limiting, Nginx rate zones |
| Resource exhaustion | Scanner timeouts, subprocess isolation |

### Elevation of Privilege
| Threat | Mitigation |
|--------|-----------|
| RBAC bypass | Permission checks on every endpoint |
| Scanner container escape | Dropped capabilities, read-only FS, non-root |
| Unauthorized scanning | Target authorization + consent + network blocks |

## Critical Attack Scenarios

### Scenario 1: Unauthorized External Scanning
**Attack:** Attacker submits competitor URL for scanning.  
**Controls:** Authorized target registration, consent checkbox, private IP blocking, audit logging.  
**Residual risk:** Low (with proper authorization workflow).

### Scenario 2: SSRF via Scan Target
**Attack:** Submit `http://169.254.169.254/` to access cloud metadata.  
**Controls:** Metadata pattern blocking, DNS resolution checks, sandbox network isolation.  
**Residual risk:** Low.

### Scenario 3: AI Prompt Injection
**Attack:** Embed instructions in finding description to manipulate remediation.  
**Controls:** System prompt hardening, input filtering, JSON-only output, schema validation.  
**Residual risk:** Medium — requires ongoing prompt tuning.

### Scenario 4: Cross-Organization IDOR
**Attack:** Access scan/findings from another organization via UUID guessing.  
**Controls:** org_id scoping on all queries, membership validation in auth dependency.  
**Residual risk:** Low.

## Security Controls Matrix

| OWASP Top 10 2021 | Control |
|-------------------|---------|
| A01 Broken Access Control | RBAC + org isolation |
| A02 Cryptographic Failures | Argon2, Fernet, TLS |
| A03 Injection | ORM, Pydantic, input sanitization |
| A04 Insecure Design | Authorization-first scanning |
| A05 Security Misconfiguration | Secure defaults, hardened Docker |
| A06 Vulnerable Components | pip-audit, npm audit, Trivy CI |
| A07 Auth Failures | MFA, lockout, token rotation |
| A08 Data Integrity | Audit logs, scan immutability |
| A09 Logging Failures | Structured logging, audit trail |
| A10 SSRF | Target validation engine |

## Recommendations

1. Deploy WAF in front of Nginx for production
2. Enable HashiCorp Vault for secret rotation
3. Implement network egress filtering on scan sandbox
4. Conduct quarterly penetration testing
5. Monitor AI outputs for anomalous remediation patterns
