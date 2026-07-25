#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi

if [ "${BOOTSTRAP_ADMIN:-false}" = "true" ]; then
  python scripts/bootstrap_admin.py
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m scripts.bootstrap_demo
fi

exec uvicorn loyalty_analytics.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
