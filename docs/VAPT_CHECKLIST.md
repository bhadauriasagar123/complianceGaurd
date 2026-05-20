# VAPT Validation Checklist

Use this checklist during professional penetration testing of ComplianceGuard.

## Pre-Engagement

- [ ] Signed authorization letter for test targets
- [ ] Test environment isolated from production data
- [ ] Emergency contact established
- [ ] Scope document defines allowed/disallowed tests

## Authentication Testing

- [ ] Brute force protection on login (lockout after 5 attempts)
- [ ] Password complexity enforcement (12+ chars, mixed case, special)
- [ ] JWT token expiration and invalidation
- [ ] Refresh token rotation and family revocation
- [ ] MFA bypass attempts (TOTP replay, brute force)
- [ ] Session fixation resistance
- [ ] Cookie flags: HttpOnly, Secure, SameSite
- [ ] Password reset token entropy and expiration

## Authorization Testing

- [ ] Horizontal privilege escalation (cross-org IDOR on scans)
- [ ] Horizontal privilege escalation (cross-org IDOR on findings)
- [ ] Horizontal privilege escalation (cross-org IDOR on reports)
- [ ] Vertical privilege escalation (viewer → admin)
- [ ] Direct object reference on UUID endpoints
- [ ] Missing function-level access control per RBAC role

## Input Validation

- [ ] SQL injection on all API parameters
- [ ] NoSQL injection (if applicable)
- [ ] XSS in stored fields (findings, targets, org name)
- [ ] Command injection via scan target field
- [ ] Path traversal in report download
- [ ] XML external entity (XXE) in Nmap XML parsing
- [ ] LDAP injection (N/A — confirm)

## SSRF Testing

- [ ] Scan target: `http://127.0.0.1`
- [ ] Scan target: `http://169.254.169.254/latest/meta-data/`
- [ ] Scan target: `http://192.168.1.1`
- [ ] Scan target: `http://10.0.0.0/8`
- [ ] Scan target: `http://[::1]`
- [ ] DNS rebinding to internal IP
- [ ] URL parser bypass attempts

## API Security

- [ ] Rate limiting effectiveness
- [ ] CSRF protection on state-changing endpoints
- [ ] CORS misconfiguration
- [ ] HTTP method tampering
- [ ] API versioning bypass
- [ ] Mass assignment via extra JSON fields
- [ ] OpenAPI spec information disclosure

## Business Logic

- [ ] Scan without authorized target record
- [ ] Scan without consent confirmation
- [ ] Scan rate limit bypass
- [ ] Cancel another user's scan
- [ ] Re-scan expired authorization target

## Infrastructure

- [ ] Docker container escape from scanner
- [ ] Network segmentation (scan-sandbox isolation)
- [ ] Non-root container execution
- [ ] TLS configuration (protocols, ciphers)
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Redis authentication
- [ ] PostgreSQL network exposure

## AI Security

- [ ] Prompt injection via finding descriptions
- [ ] Prompt injection via scan metadata
- [ ] AI output containing executable code
- [ ] Token limit bypass
- [ ] API key exposure in responses

## Logging & Monitoring

- [ ] Failed login attempts logged
- [ ] Scan creation logged with user/IP
- [ ] Audit log tamper resistance
- [ ] No sensitive data in application logs

## Post-Test

- [ ] All findings documented with severity
- [ ] Remediation recommendations provided
- [ ] Retest scheduled for critical/high findings
