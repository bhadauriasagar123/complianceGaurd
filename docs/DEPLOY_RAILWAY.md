# Deploy Backend on Railway

Run the ComplianceGuard **API on [Railway](https://railway.app)** and keep the **frontend on Vercel** (or Railway static).

Railway fits this stack well: long-running FastAPI, background scan tasks, and optional managed PostgreSQL.

> **Pricing:** Railway offers trial credits for new accounts; it is not unlimited free forever. For $0 hosting, see [DEPLOY_FREE.md](DEPLOY_FREE.md) (Render + Neon + Vercel).

---

## Architecture

```
Vercel (frontend)  →  Railway (FastAPI API)  →  Neon or Railway PostgreSQL
                              ↓
                     SCAN_MOCK_MODE=true
```

---

## Step 1 — Create Railway project

1. Sign up at [railway.app](https://railway.app).
2. **New Project** → **Deploy from GitHub repo**.
3. Select **complianceGaurd** → branch `main`.

---

## Step 2 — Configure the API service

Click the new service → **Settings**:

| Setting | Value |
|---------|--------|
| **Root Directory** | `backend` |
| **Watch Paths** | `backend/**` (optional) |

**Build:** Railway auto-detects Python and runs `pip install -r requirements.txt`.

**Start command** (Settings → Deploy → Custom Start Command), or use `railway.toml` in `backend/`:

```bash
sh scripts/railway_start.sh
```

Equivalent inline command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

**Networking:** Generate a **public domain** (Settings → Networking → Generate Domain).  
Example: `https://complianceguard-api-production.up.railway.app`

---

## Step 3 — Database

### Option A — Neon (free, recommended)

1. Create DB at [neon.tech](https://neon.tech).
2. Copy pooled URL, change prefix to `postgresql+asyncpg://...?sslmode=require`.

### Option B — Railway PostgreSQL

1. In the project: **+ New** → **Database** → **PostgreSQL**.
2. Open the Postgres service → **Connect** → copy `DATABASE_URL`.
3. Convert for async SQLAlchemy:

   ```
   postgresql://USER:PASS@HOST:PORT/railway
   → postgresql+asyncpg://USER:PASS@HOST:PORT/railway
   ```

4. Add `?sslmode=require` if connections fail.

Reference the Postgres URL on the **API service** as variable `DATABASE_URL` (Railway variable reference: `${{Postgres.DATABASE_URL}}` then fix the driver prefix in a duplicate var if needed).

---

## Step 4 — Environment variables

On the **API service** → **Variables**:

| Key | Value |
|-----|--------|
| `APP_ENV` | `production` |
| `APP_DEBUG` | `false` |
| `SCAN_MOCK_MODE` | `true` |
| `DATABASE_URL` | `postgresql+asyncpg://...` (Neon or Railway) |
| `SECRET_KEY` | 64-char hex (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `FIELD_ENCRYPTION_KEY` | Fernet key |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` |
| `PROMETHEUS_ENABLED` | `false` |
| `API_URL` | Your Railway public URL |
| `APP_URL` | Your Vercel frontend URL |
| `CORS_ORIGINS` | Same as `APP_URL` (exact, no trailing slash) |

**Do not** set values to the variable name (e.g. `APP_ENV` = `APP_ENV`). Use `production`.

Optional: leave `ANTHROPIC_API_KEY` empty.

---

## Step 5 — Deploy and verify

1. **Deploy** (or push to `main` for auto-deploy).
2. Logs should show:
   ```
   Running database migrations...
   Starting API on port ...
   ```
3. Open `https://YOUR-RAILWAY-URL/health` → `{"status":"healthy",...}`

---

## Step 6 — Connect Vercel frontend

In Vercel → **Environment Variables**:

| Key | Value |
|-----|--------|
| `VITE_API_URL` | `https://YOUR-RAILWAY-URL` (no trailing slash) |

Redeploy Vercel. Ensure Railway `CORS_ORIGINS` matches the Vercel URL.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `render_start.sh` / script not found | Root Directory must be `backend`; use `sh scripts/railway_start.sh` |
| `APP_ENV` validation error | Set `APP_ENV` = `production` (not the literal text `APP_ENV`) |
| DB connection failed | Use `postgresql+asyncpg://` and `sslmode=require` for Neon |
| Build uses Python 3.14 issues | `backend/runtime.txt` and `nixpacks.toml` pin 3.12 |
| CORS errors | `CORS_ORIGINS` must exactly match Vercel URL |
| Service sleeps | Railway hobby usage; upgrade plan or use Render free tier |

---

## Render vs Railway

| | Render (free) | Railway |
|--|---------------|---------|
| Cost | $0 tier | Trial credits, then usage-based |
| Cold start | Yes (free tier) | Faster on paid usage |
| Postgres | External (Neon) | Built-in plugin |
| Background tasks | Works | Works |
| Config in repo | `render.yaml` | `backend/railway.toml` |

You can run **only the backend** on Railway and keep the frontend on Vercel.

---

## Push config to GitHub

```powershell
git add backend/railway.toml backend/nixpacks.toml backend/scripts/railway_start.sh docs/DEPLOY_RAILWAY.md
git commit -m "Add Railway deployment config for backend"
git push
```

Repository: [github.com/bhadauriasagar123/complianceGaurd](https://github.com/bhadauriasagar123/complianceGaurd)
