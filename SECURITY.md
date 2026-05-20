# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

**Do not** open public GitHub issues for security vulnerabilities.

Email: security@complianceguard.io

Include:
- Description and impact
- Steps to reproduce
- Affected component/version
- Suggested remediation (if any)

We respond within **48 hours** and provide status updates every 72 hours until resolution.

## Security Architecture Summary

### Authentication (OWASP ASVS V2-V3)
- Argon2id password hashing
- JWT access tokens (15 min) + rotating refresh tokens (7 days)
- HttpOnly, Secure, SameSite cookies
- TOTP MFA with encrypted secrets
- Account lockout after 5 failed attempts
- Session revocation support

### Authorization (OWASP ASVS V4)
- Role-Based Access Control (5 roles)
- Organization-level data isolation
- Route and resource-level permission checks
- IDOR prevention via org_id scoping on all queries

### Input Validation (OWASP ASVS V5)
- Pydantic v2 strict schema validation
- SQLAlchemy ORM (parameterized queries only)
- Anti-SSRF target validation
- Shell metacharacter blocking in scanner commands
- Bleach sanitization for PDF/report output

### API Security (OWASP ASVS V13-V14)
- Rate limiting (60 req/min default)
- CSRF double-submit cookie pattern
- Strict CORS allowlist
- Security headers (CSP, HSTS, X-Frame-Options)
- API versioning (/api/v1)

### Scan Security
- Authorization gate before every scan
- Explicit consent requirement
- Private IP/localhost/metadata blocking
- Sandboxed scanner containers with dropped capabilities
- Subprocess timeout enforcement
- Per-organization scan rate limits

### Secrets Management
- No secrets in source code
- `.env.example` template only
- HashiCorp Vault integration structure
- Fernet encryption for sensitive DB fields

## Secure Development Lifecycle

1. **SAST**: Semgrep, Bandit on every PR
2. **Dependency scanning**: pip-audit, npm audit, Safety
3. **Container scanning**: Trivy on Docker images
4. **Secret scanning**: Gitleaks in CI
5. **DAST**: OWASP ZAP baseline in staging
6. **Security unit tests**: auth bypass, IDOR, SSRF, injection

## Hardening Recommendations

### Production Checklist
- [ ] Set `APP_ENV=production`, `APP_DEBUG=false`
- [ ] Enable `COOKIE_SECURE=true`
- [ ] Configure TLS termination at Nginx/load balancer
- [ ] Rotate `SECRET_KEY` and `FIELD_ENCRYPTION_KEY`
- [ ] Connect HashiCorp Vault for secrets
- [ ] Enable Sentry error tracking
- [ ] Configure OpenTelemetry export
- [ ] Restrict scanner sandbox network egress
- [ ] Enable PostgreSQL SSL connections
- [ ] Set up log aggregation and alerting
- [ ] Review and customize CORS origins
- [ ] Disable API docs in production (default)

### Cryptography
- Passwords: Argon2id (time=3, memory=64MB)
- Tokens: HS256 JWT with 256-bit secret minimum
- Field encryption: Fernet (AES-128-CBC + HMAC)
- No MD5/SHA1 for security purposes

## Bug Bounty

Contact security@complianceguard.io for responsible disclosure program details.
