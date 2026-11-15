#!/bin/sh
set -eu
python /app/deploy/wait_for_db.py
python /app/manage.py migrate --noinput
python /app/manage.py collectstatic --noinput
# Seeding is explicitly opt-in; it only uses bundled lightweight reference images.
if [ "${NA_SEED_CATALOG:-0}" = '1' ]; then
  python /app/manage.py seed_new_arrivals
fi
exec gunicorn valaproject.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile -
