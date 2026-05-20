# ComplianceGuard

AI-powered infrastructure compliance and security assessment platform for enterprise teams.

**Repository:** [github.com/bhadauriasagar123/complianceGaurd](https://github.com/bhadauriasagar123/complianceGaurd)

## Features

- **Authorized scanning only** — targets require explicit ownership verification and consent
- **Multi-scanner orchestration** — Nmap, Nuclei, OWASP ZAP (Docker/production)
- **Unified findings engine** — deduplication, severity normalization, CVSS mapping
- **Compliance mapping** — HIPAA, GDPR, PCI-DSS, OWASP Top 10
- **AI remediation** — Claude-powered guidance (optional `ANTHROPIC_API_KEY`)
- **Enterprise PDF reports** — ReportLab-generated assessments
- **RBAC multi-tenancy** — organization isolation with role levels
- **Full audit trail** — immutable logging of security-relevant actions

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   React UI  │────▶│   FastAPI   │────▶│ PostgreSQL / SQLite │
│  (Vite/TS)  │     │   API       │     └──────────────────┘
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐     ┌──────────────────┐
                    │   Celery    │────▶│ Scanner Sandbox  │
                    │   Workers   │     │ Nmap/Nuclei/ZAP  │
                    └──────┬──────┘     └──────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    └─────────────┘
```

---

## Prerequisites

| Tool | Version | Required for |
|------|---------|--------------|
| **Python** | 3.12+ (3.14 tested) | Backend API |
| **Node.js** | 20+ | Frontend |
| **Git** | Latest | Clone & push |
| **Docker** | Optional | Production / full scan pipeline |

---

## Quick Start (Windows — no Docker)

This is the **recommended local path**. Uses SQLite, Vite API proxy, and dev scan mock (no Redis, Nmap, or ZAP required).

### 1. Clone the repository

```powershell
git clone https://github.com/bhadauriasagar123/complianceGaurd.git
cd complianceGaurd
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

Edit `.env` and set at minimum:

| Variable | How to generate |
|----------|-----------------|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FIELD_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

`ANTHROPIC_API_KEY` is optional for local UI/testing (AI remediation skipped if empty).

> **Never commit `.env` or `frontend/.env`** — they are listed in `.gitignore`.

### 3. Install dependencies

**Backend:**

```powershell
cd backend
python -m pip install -r requirements.txt
cd ..
```

**Frontend:**

```powershell
cd frontend
npm ci
cd ..
```

### 4. Start everything (one command)

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
```

This opens two windows:

- **API** → http://127.0.0.1:8000 (SQLite at `backend/dev.db`)
- **Frontend** → http://127.0.0.1:5173 (proxies `/api` to the API — no CORS issues)

### 5. Use the app

1. Open http://127.0.0.1:5173/register and create an account.
2. Go to **Scans** → **Add target** (e.g. `https://example.com`).
3. **New scan** → select target, confirm consent, start scan.

Scans complete in **dev mock mode** on SQLite (status moves to `completed` without external scanners).

### Manual start (two terminals)

**Terminal 1 — API:**

```powershell
powershell -ExecutionPolicy Bypass -File backend\run-api.ps1
```

**Terminal 2 — Frontend:**

```powershell
powershell -ExecutionPolicy Bypass -File frontend\run-dev.ps1
```

---

## Deploy online for free (production)

Host on **Vercel + Render + Neon** at **$0/month** (mock scans, no paid APIs required).

**Step-by-step guide:** [docs/DEPLOY_FREE.md](docs/DEPLOY_FREE.md)

Summary:

1. [Neon](https://neon.tech) — free PostgreSQL → `DATABASE_URL`
2. [Render](https://render.com) — deploy API from `render.yaml`, set `SCAN_MOCK_MODE=true`
3. [Vercel](https://vercel.com) — deploy `frontend/` with `VITE_API_URL=https://your-api.onrender.com`

---

## Quick Start (Docker — full stack)

Use this for production-like scans with PostgreSQL, Redis, Celery, and scanner containers.

### 1. Configure environment

```bash
cp .env.example .env
# Set SECRET_KEY, FIELD_ENCRYPTION_KEY, and optional ANTHROPIC_API_KEY
```

### 2. Start infrastructure

```bash
cd docker
docker compose up -d postgres redis
```

### 3. Migrate database

```bash
cd ../backend
pip install -r requirements.txt
alembic upgrade head
```

### 4. Run services

```bash
# API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Frontend (separate terminal)
cd ../frontend && npm ci && npm run dev
```

Open http://localhost:5173

---

## Run tests (no Docker)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run-all-tests.ps1
```

Runs Ruff lint, pytest (SQLite in-memory), and frontend production build.

---

## Push this project to GitHub

If you are publishing from your machine for the first time:

```powershell
cd "D:\Compliance gaurd"   # or your clone path

# Initialize git (skip if already a repo)
git init
git branch -M main

# Verify secrets are NOT staged
git status
# .env and backend/dev.db must NOT appear

git add .
git commit -m "Initial commit: ComplianceGuard platform"

git remote add origin https://github.com/bhadauriasagar123/complianceGaurd.git
git push -u origin main
```

If the remote already has a README/license and rejects the push:

```powershell
git pull origin main --rebase
git push -u origin main
```

Or force-push only to an **empty** repo you own:

```powershell
git push -u origin main --force
```

Authenticate with GitHub via browser (Git Credential Manager) or a [personal access token](https://github.com/settings/tokens) when prompted.

**CI workflow note:** The file `.github/workflows/ci.yml` exists locally but was excluded from the first push because GitHub requires the `workflow` scope on your PAT. To publish it:

1. Create a token at [github.com/settings/tokens](https://github.com/settings/tokens) with **repo** and **workflow** scopes.
2. Run:

```powershell
git add .github/workflows/ci.yml
git commit -m "Add GitHub Actions CI workflow"
git push
```

---

## Clone after publish

```powershell
git clone https://github.com/bhadauriasagar123/complianceGaurd.git
cd complianceGaurd
```

Then follow **Quick Start (Windows — no Docker)** above.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **CORS / network errors** | Use http://127.0.0.1:5173 (not direct :8000 from the browser). Keep `VITE_API_URL` empty in `frontend/.env`. |
| **500 on POST /scans** | Restart API: `backend\run-api.ps1`. Avoid editing backend files while creating scans (uvicorn reload can cancel background tasks). |
| **Database is locked** | Stop duplicate API processes in Task Manager, restart `run-api.ps1` once. |
| **Empty target dropdown** | Add a target via **Add target** on the Scans page first. |
| **401 on login right after register** | Wait 1 second and retry, or refresh the page. |
| **Port 8000 / 5173 in use** | `netstat -ano \| findstr :8000` then stop the PID, or change ports in `run-api.ps1` / `run-dev.ps1`. |
| **Docker not installed** | Use the Windows SQLite quick start above — no Docker required. |

API docs (dev only): http://127.0.0.1:8000/api/docs

---

## Security architecture

| Control | Implementation |
|---------|----------------|
| Authentication | JWT access + rotating refresh tokens, HttpOnly cookies |
| MFA | TOTP with encrypted secret storage |
| Authorization | RBAC with org-level isolation |
| Scan safety | Private IP/localhost/metadata blocking, consent gates |
| API security | Rate limiting, CSRF, CORS, CSP |
| Audit | Immutable `audit_logs` table |

See [SECURITY.md](SECURITY.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Scanning limitations

ComplianceGuard **will reject**:

- localhost and loopback addresses
- RFC1918 private networks
- Cloud metadata endpoints (169.254.x)
- Targets without an authorization record
- Scans without explicit consent

Only scan systems you own or are explicitly authorized to test.

## Project structure

```
complianceGaurd/
├── backend/          # FastAPI application
├── frontend/         # React SPA (Vite)
├── docker/           # Docker Compose
├── k8s/              # Kubernetes manifests
├── terraform/        # Infrastructure as Code
├── docs/             # Security & compliance docs
├── scripts/          # Dev & test scripts (Windows)
├── postman/          # API collection
└── .github/workflows/# CI/CD
```

## Environment variables

See [.env.example](.env.example). Critical entries:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing (min 32 chars) |
| `DATABASE_URL` | Overridden to SQLite by `run-api.ps1` in dev |
| `FIELD_ENCRYPTION_KEY` | Fernet key for MFA secrets |
| `ANTHROPIC_API_KEY` | Optional — AI remediation |

## License

Proprietary — All rights reserved.
