#!/usr/bin/env sh
# ClauseRadar local dev bootstrap (macOS/Linux)
# Usage: sh scripts/dev_setup.sh
set -eu
cp -n .env.example .env 2>/dev/null || true
python3 -m pip install --upgrade pip
python3 -m pip install -r backend/requirements.txt
python3 backend/manage.py migrate
echo "Done. Run: python3 backend/manage.py runserver  +  (cd frontend && npm install && npm run dev)"
