# Run ComplianceGuard locally with Docker (Windows)

## Step 1 — Install Docker Desktop

1. Download: **https://www.docker.com/products/docker-desktop/**
2. Run the installer (enable **WSL 2** if prompted).
3. Restart Windows if asked.
4. Open **Docker Desktop** and wait until it shows **Engine running**.

Verify in PowerShell:

```powershell
docker --version
docker compose version
```

---

## Step 2 — Prepare environment

From the project folder:

```powershell
cd "d:\Compliance gaurd"
```

Ensure `.env` exists (copy from example if needed):

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Your `.env` must include at least:

```env
SECRET_KEY=your-32-char-or-longer-secret-key-here
FIELD_ENCRYPTION_KEY=8vP2mKqR9xT4nW7jL1hF5sY0bN6cA3eU=
```

Generate a new secret if needed:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 3 — Start the stack

### Option A — Quick (HTTP probe, like Render) — recommended first

Faster build, no Nmap/Nuclei/ZAP. Good to verify Docker works.

```powershell
.\scripts\start-docker.ps1 -Mode Quick
```

### Option B — Full scanning (Nmap, Nuclei, ZAP, Juice Shop)

First run can take **15–30 minutes** (downloads images + Nuclei templates).

```powershell
.\scripts\start-docker.ps1 -Mode Full
```

Or manually:

```powershell
cd docker
docker compose --profile scanning up -d --build
```

---

## Step 4 — Open the app

| Service | URL |
|---------|-----|
| **UI** | http://localhost:5173 |
| **API** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |
| **Juice Shop** (Full mode only) | http://localhost:3000 |

1. Register a new account at http://localhost:5173  
2. **Scans → Add target**  
3. **New scan → Start**

---

## What target URL to use

| Mode | Target URL |
|------|------------|
| **Quick** | `https://testphp.vulnweb.com` |
| **Full (Juice Shop)** | `http://juice-shop:3000` |
| **Full (from browser)** | `http://host.docker.internal:3000` |

---

## Stop the stack

```powershell
cd "d:\Compliance gaurd\docker"
docker compose --profile scanning down
```

Quick mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.quick.yml down
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker` not recognized | Install Docker Desktop, restart PC, open Docker Desktop |
| Build fails | Ensure Docker Desktop is running; retry with `docker compose build --no-cache api` |
| Port 5173 / 8000 in use | Stop other apps or change ports in `docker-compose.yml` |
| 401 / CSRF on login | Hard refresh; open http://localhost:5173 (not 127.0.0.1) |
| Scan stays running (Full mode) | Check logs: `docker compose logs -f worker` — ZAP/Nuclei can take 10+ min |
| API not healthy | `docker compose logs api` — wait for migrations to finish |

---

## Manual commands (reference)

```powershell
cd "d:\Compliance gaurd\docker"

# Status
docker compose ps

# Logs
docker compose logs -f api worker

# Rebuild API only
docker compose build api --no-cache
docker compose up -d api
```
