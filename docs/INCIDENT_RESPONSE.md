# Incident Response Playbook

## Severity Classification

| Level | Description | Response Time |
|-------|-------------|---------------|
| SEV-1 | Active breach, unauthorized scanning, data exfiltration | 15 minutes |
| SEV-2 | Vulnerability with known exploit in production | 1 hour |
| SEV-3 | Security weakness without active exploitation | 24 hours |
| SEV-4 | Low-risk finding, hardening opportunity | 72 hours |

## Response Team

| Role | Responsibility |
|------|---------------|
| Incident Commander | Coordinates response, external communication |
| Security Lead | Technical investigation, containment |
| Engineering Lead | Patches, deployments |
| Legal/Compliance | Regulatory notification if required |

## Phase 1: Detection & Triage (0-15 min)

1. Confirm alert via multiple sources (Sentry, audit logs, WAF)
2. Assign severity level
3. Open incident channel (#incident-YYYYMMDD)
4. Document initial timeline

### Key Indicators
- Spike in failed login attempts
- Scans against unauthorized targets
- Cross-organization data access in audit logs
- Unusual outbound traffic from scan-sandbox
- AI API usage anomalies

## Phase 2: Containment (15-60 min)

### Unauthorized Scanning Detected
```bash
# Revoke all active sessions for affected org
# Cancel in-flight scans
# Block source IP at WAF/Nginx
```

1. Disable affected user accounts
2. Cancel active Celery scan tasks
3. Review audit_logs for `scan_created` events
4. Block attacker IP at infrastructure level

### Data Breach Suspected
1. Rotate `SECRET_KEY` (forces re-authentication)
2. Revoke all refresh token families
3. Rotate `ANTHROPIC_API_KEY`
4. Enable enhanced audit logging
5. Snapshot database for forensic analysis

### Container Compromise
```bash
docker compose -f docker/docker-compose.yml stop worker scanner-nmap
kubectl delete pods -l app=complianceguard-worker
```

## Phase 3: Eradication (1-24 hours)

1. Identify root cause (code vulnerability, misconfiguration, credential leak)
2. Develop and test patch
3. Deploy via emergency change process
4. Verify fix with security test suite

```bash
cd backend && pytest tests/security/ -v
```

## Phase 4: Recovery (24-72 hours)

1. Restore services incrementally (database → API → workers → scanners)
2. Monitor audit logs and metrics for 48 hours
3. Notify affected customers per contractual obligations
4. GDPR breach notification within 72 hours if personal data affected

## Phase 5: Post-Incident (1 week)

1. Complete incident report with timeline
2. Update threat model if new attack vector discovered
3. Add regression tests for vulnerability
4. Conduct blameless post-mortem
5. Update VAPT checklist with new test cases

## Communication Templates

### Internal (SEV-1)
```
INCIDENT SEV-1: [Brief description]
Status: Investigating / Contained / Resolved
IC: [Name]
Impact: [Customer data / Scan abuse / Service outage]
Next update: [Time]
```

### Customer Notification
```
We detected a security event affecting ComplianceGuard on [date].
Scope: [Description without exposing exploit details]
Actions taken: [Containment measures]
Your action required: [Password reset / MFA enable / None]
Contact: security@complianceguard.io
```

## Regulatory Considerations

| Regulation | Notification Requirement |
|------------|-------------------------|
| GDPR Art. 33 | 72 hours to supervisory authority if personal data breach |
| HIPAA | 60 days to HHS if >500 individuals affected |
| PCI-DSS | Immediate to payment brands if cardholder data involved |

## Evidence Preservation

1. Export audit_logs for incident timeframe
2. Preserve application logs (structured JSON)
3. Snapshot affected containers/VMs
4. Document all commands executed during response
5. Chain of custody log for forensic artifacts
