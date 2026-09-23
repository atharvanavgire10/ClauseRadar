#!/usr/bin/env bash
# scripts/vercel-build.sh
# Production build script for Vercel native Django deployment.
# Runs migrations only in production when DATABASE_URL is provided,
# builds the React SPA, and syncs frontend assets into Django templates & static dirs.

set -euo pipefail

echo "==> [vercel-build] Starting ClauseRadar build"
echo "==> [vercel-build] Environment: VERCEL_ENV=${VERCEL_ENV:-<unset>} VERCEL=${VERCEL:-<unset>}"

# Locate Python executable
PYTHON_BIN="python"
if [ -f ".vercel/python/.venv/bin/python" ]; then
  PYTHON_BIN=".vercel/python/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "==> [vercel-build] Using Python: $PYTHON_BIN ($($PYTHON_BIN --version 2>&1 || true))"

# Check Django availability
$PYTHON_BIN -c "import django; print('==> [vercel-build] Django version:', django.__version__)"

# If in production, execute database migrations
if [ "${VERCEL_ENV:-}" = "production" ]; then
  echo "==> [vercel-build] Production environment detected"
  if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set in production!" >&2
    exit 1
  fi

  echo "==> [vercel-build] Checking migration status..."
  $PYTHON_BIN backend/manage.py showmigrations

  echo "==> [vercel-build] Applying database migrations..."
  $PYTHON_BIN backend/manage.py migrate --noinput

  echo "==> [vercel-build] Migrations completed successfully"

  echo "==> [vercel-build] Ensuring public evaluation workspace is seeded..."
  $PYTHON_BIN backend/manage.py seed_eval
  echo "==> [vercel-build] seed_eval completed successfully"
else
  echo "==> [vercel-build] Non-production environment (${VERCEL_ENV:-<unset>}); skipping database migrations"
fi

# Build React SPA
echo "==> [vercel-build] Installing frontend dependencies..."
npm --prefix frontend ci

echo "==> [vercel-build] Building frontend for production..."
VITE_API_URL="${VITE_API_URL:-same-origin}" npm --prefix frontend run build:prod

# Sync SPA assets into Django
echo "==> [vercel-build] Syncing SPA assets to Django directories..."
node frontend/scripts/sync-spa.js

echo "==> [vercel-build] Build finished successfully"

