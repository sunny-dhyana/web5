#!/bin/bash
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  Mercury Marketplace — Starting Up"
echo "═══════════════════════════════════════════════════"

# Ensure the data directory is writable
mkdir -p /data
chown -R "$(id -u):$(id -g)" /data 2>/dev/null || true

# Initialise database tables
echo "→ Initializing database schema…"
python -c "
from app.database import init_db
init_db()
print('  Schema ready.')
"

# Seed demo data (safe to run multiple times)
echo "→ Checking seed data…"
python seed.py

echo ""
echo "→ Starting API server on http://0.0.0.0:8005"
echo "  API docs: http://localhost:8005/api/docs"
echo "  App:      http://localhost:8005"
echo "═══════════════════════════════════════════════════"

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8005 \
    --workers 1 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
