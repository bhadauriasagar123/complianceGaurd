# Security scanning guide

ComplianceGuard supports two scanning modes:

| Mode | Where | What it finds |
|------|--------|----------------|
| **Cloud / mock** (`SCAN_MOCK_MODE=true`) | Render, Vercel, local SQLite | Real **HTTP header/cookie** issues + **demo catalog** for practice sites |
| **Full scanners** (`SCAN_MOCK_MODE=false`) | Docker Compose | **Nmap**, **Nuclei**, **OWASP ZAP** against authorized targets |

> Only scan systems you own or have **written authorization** to test.

---

## Cloud deployment (Render) — passive + demo findings

Set on Render:

```env
SCAN_MOCK_MODE=true
SCAN_MOCK_HTTP_PROBE=true
```

Each completed scan will:

1. **HTTP probe** — GET the target URL and report real misconfigurations (missing HSTS, CSP, cookie flags, server banners, cleartext HTTP).
2. **Demo catalog** — extra educational findings when the host matches known practice apps (see below).

View results: **Dashboard → Findings** (select a completed scan).

### Legal practice targets (authorized demos)

Add these as **Authorized targets**, then run a scan:

| Target URL | Purpose |
|------------|---------|
| `https://testphp.vulnweb.com` | Acunetix public test site |
| `https://zero.webappsecurity.com` | Practice banking app |
| `https://demo.owasp-juice.shop` | OWASP Juice Shop (hosted demo) |

Do **not** scan third-party production sites without permission.

---

## Docker — full vulnerability scanning (Nmap, Nuclei, ZAP)

### 1. Start the stack with scanning profile

```bash
cd docker
docker compose --profile scanning up -d --build
```

This starts API, worker, Redis, Postgres, ZAP, **Juice Shop**, and installs **Nmap + Nuclei** in the worker.

### 2. Configure environment

Copy `.env.example` to `.env` and set:

```env
SCAN_MOCK_MODE=false
SCAN_MOCK_HTTP_PROBE=true
```

### 3. Register a target reachable from the worker

| Target | When to use |
|--------|-------------|
| `http://juice-shop:3000` | Scan from **worker** container (recommended) |
| `http://localhost:3000` | Only if you map port 3000 and scan from host network |

In the UI: **Scans → Add target** → URL above → **New scan** → enable Nmap, Nuclei, ZAP.

### 4. View findings

**Findings** page → select the completed scan.

Scans may take **5–30 minutes** depending on target and templates.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_MOCK_MODE` | `false` | Use passive/mock pipeline instead of Nmap/Nuclei/ZAP |
| `SCAN_MOCK_HTTP_PROBE` | `true` | Run HTTP security probe in mock mode |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 0 findings on Render | Ensure `SCAN_MOCK_HTTP_PROBE=true`; target must be public HTTPS/HTTP (not localhost) |
| Scan pending forever | Redeploy latest API; `SCAN_MOCK_MODE=true` runs inline on create |
| Docker scan fails | Set `SCAN_MOCK_MODE=false`; check worker logs; ensure target hostname resolves inside Docker |
| Nuclei empty | Worker image runs `nuclei -update-templates` on build; first run may be slow |
