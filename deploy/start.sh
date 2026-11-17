#!/bin/sh
set -eu
# Ne jamais lancer migrate ni Gunicorn si les photos seraient éphémères.
if [ "${VALADEPLOY_MODE:-0}" = "1" ] && [ "${MEDIA_STORAGE:-}" = "local" ]; then
  [ "${VALADEPLOY_LOCAL_MEDIA_VOLUME:-0}" = "1" ] || {
    echo 'Volume média local non autorisé' >&2; exit 72;
  }
  python - <<'PYMEDIA'
import os
import tempfile
root = '/app/media'
if not os.path.ismount(root):
    raise SystemExit('Volume média absent : démarrage refusé AVANT migration')
with tempfile.NamedTemporaryFile(prefix='.na-media-check-', dir=root, delete=True) as handle:
    handle.write(b'volume-access-ok')
    handle.flush()
PYMEDIA
fi
python /app/deploy/wait_for_db.py
python /app/manage.py migrate --noinput
python /app/manage.py collectstatic --noinput
# Seeding is explicitly opt-in; it only uses bundled lightweight reference images.
if [ "${NA_SEED_CATALOG:-0}" = '1' ]; then
  python /app/manage.py seed_new_arrivals
fi
exec gunicorn valaproject.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile -
