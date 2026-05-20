# Deploy ComplianceGuard Online (100% Free)

Host the full app on **free tiers** — no credit card required for basic use.

| Layer | Free service | Role |
|-------|--------------|------|
| **Frontend** | [Vercel](https://vercel.com) | React static site |
| **API** | [Render](https://render.com) | FastAPI backend |
| **Database** | [Neon](https://neon.tech) | PostgreSQL |

**Total cost: $0/month** for demo and light use.

> **What you get on free tier:** Auth, dashboard, targets, scans (mock pipeline), findings UI, audit logs.  
> **What you do not get for free:** Real Nmap/Nuclei/ZAP scans (need VPS/Docker), always-on API (Render sleeps), unlimited AI (Anthropic is paid).

---

## Architecture (free)

```
Browser → Vercel (React) → Render (FastAPI) → Neon (PostgreSQL)
                              ↓
                    SCAN_MOCK_MODE=true
                    (no Redis / Celery / scanners)
```

---

## Part 1 — Neon database (5 minutes)

1. Sign up at [neon.tech](https://neon.tech).
2. Create a project (e.g. `complianceguard`).
3. Open **Dashboard → Connection details**.
4. Copy the **Pooled connection** string. It looks like:
   ```
   postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
5. Change the prefix for this app:
   ```
      //user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
   Save this as your `DATABASE_URL`.

---

## Part 2 — Render API (15 minutes)

1. Sign up at [render.com](https://render.com).
2. **New → Blueprint** (or **Web Service**).
3. Connect your GitHub repo: [complianceGaurd](https://github.com/bhadauriasagar123/complianceGaurd).
4. Set **Root Directory** to `backend` (required for monorepo).
5. **Start Command** (copy exactly, no extra spaces):

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Or, after the repo includes `backend/scripts/render_start.sh`:

```bash
sh scripts/render_start.sh
```

6. Render Blueprint: optional `render.yaml` at repo root.
5. In the service **Environment** tab, set:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Your Neon `postgresql+asyncpg://...` string |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FIELD_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SCAN_MOCK_MODE` | `true` |
| `APP_ENV` | `production` |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (set after Part 3) |
| `APP_URL` | `https://YOUR-APP.vercel.app` |
| `API_URL` | `https://YOUR-SERVICE.onrender.com` |
| `PROMETHEUS_ENABLED` | `false` |

6. Deploy. Wait for **Live** status.
7. Test: open `https://YOUR-SERVICE.onrender.com/health` → `{"status":"healthy",...}`.

**Render free notes:**

- Service **sleeps after ~15 minutes** of no traffic. First visit may take **30–60 seconds** (cold start).
- Free instances have **512 MB RAM** — mock scans are tuned for this.

---

## Part 3 — Vercel frontend (10 minutes)

1. Sign up at [vercel.com](https://vercel.com).
2. **Add New → Project** → import `complianceGaurd` from GitHub.
3. Configure:

| Setting | Value |
|---------|--------|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

4. **Environment variables:**

| Key | Value |
|-----|--------|
| `VITE_API_URL` | `https://YOUR-SERVICE.onrender.com` (no trailing slash) |

5. Deploy. Note your URL, e.g. `https://complianceguard.vercel.app`.

6. **Update Render** `CORS_ORIGINS` and `APP_URL` with this exact Vercel URL, then **Redeploy** the API.

---

## Part 4 — First use

1. Open your Vercel URL.
2. **Register** a new account (data is stored in Neon).
3. **Scans → Add target** → e.g. `https://example.com`.
4. **New scan** → confirm consent → start.

Scans run in **mock mode** (`SCAN_MOCK_MODE=true`): they complete without external scanner tools.

---

## Generate secrets (local machine)

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **CORS error in browser** | `CORS_ORIGINS` on Render must exactly match the Vercel URL (https, no trailing slash). Redeploy API. |
| **403 on register/login (CSRF)** | Deploy latest `main` (CSRF token via `/api/v1/auth/csrf`). Redeploy **Vercel** frontend too. Set `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`. |
| **CSRF / login fails** | Set `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none`. Ensure `VITE_API_URL` points to Render. |
| **API very slow first load** | Render free tier cold start — wait 60s and refresh. |
| **Database connection error** | Use Neon **pooled** URL with `postgresql+asyncpg://` and `sslmode=require`. |
| **`sslmode` / asyncpg error** | Deploy latest `main` (fix strips `sslmode` automatically). |
| **`APP_ENV` validation error** | Set `APP_ENV` = `production` (not the literal text `APP_ENV`). |
| **Exited with status 1 (no details)** | Set **Start Command** to `sh scripts/render_start.sh`, add env `PYTHON_VERSION` = `3.12.8`, redeploy. Read logs above the exit line. |
| **alembic / relation already exists** | In Neon SQL editor: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then redeploy. |
| **500 after deploy** | Check Render **Logs** tab after preflight lines. |
| **Scans stuck pending** | Confirm `SCAN_MOCK_MODE=true` on Render. |

---

## Optional upgrades (still free or low cost)

| Need | Option |
|------|--------|
| **Redis / Celery** | [Upstash](https://upstash.com) free Redis — set `SCAN_MOCK_MODE=false` and add Redis URLs |
| **Always-on API** | Render paid $7/mo — only if you need 24/7 uptime |
| **Custom domain** | Vercel + Render free SSL for your domain |
| **AI remediation** | Anthropic API key (pay-per-use) in Render env |

---

## Alternative free frontends

Same `VITE_API_URL` pointing to Render:

- **Netlify** — root `frontend`, build `npm run build`, publish `dist`
- **Cloudflare Pages** — same build settings

---

## Security reminder

- Only scan targets you are **authorized** to test.
- Free tiers are for **demo / development** — not regulated production workloads.
- Rotate `SECRET_KEY` if ever exposed.

---

## Quick checklist

- [ ] Neon `DATABASE_URL` with `postgresql+asyncpg://`
- [ ] Render deployed, `/health` returns 200
- [ ] `SCAN_MOCK_MODE=true`
- [ ] Vercel `VITE_API_URL` = Render URL
- [ ] `CORS_ORIGINS` = Vercel URL
- [ ] Register + create scan works

Repository: [github.com/bhadauriasagar123/complianceGaurd](https://github.com/bhadauriasagar123/complianceGaurd)
