#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."

echo "=== ComplianceGuard startup ==="
echo "Python: $(python --version 2>&1)"

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is not set in Render environment variables."
  exit 1
fi

echo "Preflight (config + DB URL)..."
python -c "
from app.core.config import get_settings
from app.core.database import prepare_asyncpg_url

s = get_settings()
url, ssl_args = prepare_asyncpg_url(s.database_url)
print('APP_ENV =', s.app_env)
print('DB URL scheme OK =', url.startswith('postgresql+asyncpg'))
print('SSL connect_args =', ssl_args)
if s.app_env not in ('development', 'staging', 'production'):
    raise SystemExit(f'Invalid APP_ENV: {s.app_env!r}')
if not url.startswith('postgresql+asyncpg') and not url.startswith('sqlite'):
    raise SystemExit('DATABASE_URL must use postgresql+asyncpg:// or sqlite+aiosqlite://')
"

echo "Running database migrations..."
if ! alembic upgrade head; then
  echo "ERROR: alembic upgrade failed."
  echo "If Neon already has tables, reset the DB in Neon console or run: alembic stamp head"
  exit 1
fi

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
