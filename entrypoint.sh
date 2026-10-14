#!/usr/bin/env bash
# Container entrypoint: wait for Postgres, migrate, seed, collect statics,
# then exec gunicorn. Logs each step so `docker logs api` is readable.
set -euo pipefail

say() { printf '→ %s\n' "$*"; }

say "waiting for postgres…"
until pg_isready \
    -h "${POSTGRES_HOST:-postgres}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-postgres}" \
    -q; do
  sleep 0.5
done
say "postgres is ready"

say "applying migrations"
python manage.py migrate --noinput

say "seeding RBAC permission registry"
python manage.py seed_rbac

if [[ "${SEED_DEMO:-false}" == "true" ]]; then
  say "seeding demo data (SEED_DEMO=true)"
  python manage.py seed_demo
fi

say "collecting static files"
python manage.py collectstatic --noinput --clear

say "starting gunicorn on 0.0.0.0:8000 (workers=${GUNICORN_WORKERS:-3})"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:8000" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 30 \
  --access-logfile - \
  --error-logfile -
