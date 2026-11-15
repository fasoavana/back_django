"""Wait for ValaDeploy PostgreSQL component to accept connections."""
import os, sys, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'valaproject.settings')
import django
django.setup()
from django.db import connections
for attempt in range(1, 46):
    try:
        connections['default'].ensure_connection()
        print('PostgreSQL accessible', flush=True)
        break
    except Exception as exc:
        if attempt == 45:
            print('PostgreSQL inaccessible après 90 secondes : ' + type(exc).__name__, file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
