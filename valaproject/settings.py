import os
from pathlib import Path
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'development-only-change-me')
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
if not DEBUG and SECRET_KEY == 'development-only-change-me':
    raise RuntimeError('DJANGO_SECRET_KEY doit être défini en production.')
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,backend').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if v.strip()]
CORS_ALLOWED_ORIGINS = [v.strip() for v in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if v.strip()]
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework_simplejwt', 'corsheaders', 'shop',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'valaproject.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [],
    'APP_DIRS': True, 'OPTIONS': {'context_processors': [
    'django.template.context_processors.debug', 'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'valaproject.wsgi.application'
# ValaDeploy native stacks generate DB_URL with the nonstandard pgsql:// scheme.
# Convert it to an alias supported by dj-database-url, without logging credentials.
_DB_URL = os.environ.get('DATABASE_URL') or os.environ.get('DB_URL')
if _DB_URL and _DB_URL.startswith('pgsql://'):
    _DB_URL = 'postgresql://' + _DB_URL[len('pgsql://'):]
if os.environ.get('VALADEPLOY_MODE') == '1' and not _DB_URL:
    raise RuntimeError('DB_URL absent : le composant DATABASE doit être déployé avant BACK.')
DATABASES = {'default': dj_database_url.parse(_DB_URL, conn_max_age=300) if _DB_URL else
             dj_database_url.parse('sqlite:///' + str(BASE_DIR / 'db.sqlite3'), conn_max_age=300)}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication', 'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '120/hour', 'user': '600/hour', 'orders': '8/hour', 'uploads': '12/hour', 'auth': '20/hour'},
    'DEFAULT_PAGINATION_CLASS': 'shop.pagination.CataloguePagination',
    'PAGE_SIZE': 24,
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30), 'REFRESH_TOKEN_LIFETIME': timedelta(days=1), 'AUTH_HEADER_TYPES': ('Bearer',)}
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Indian/Antananarivo'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# ValaDeploy does not mount persistent volumes for FRONT/BACK components.
# Use external S3-compatible storage (e.g. MinIO or S3) for real orders/photos.
MEDIA_STORAGE = os.environ.get('MEDIA_STORAGE', 'local').lower()
if os.environ.get('VALADEPLOY_MODE') == '1' and not DEBUG and MEDIA_STORAGE != 's3':
    raise RuntimeError('Production ValaDeploy: MEDIA_STORAGE=s3 obligatoire pour conserver les photos.')
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if MEDIA_STORAGE == 's3':
    required = ('AWS_STORAGE_BUCKET_NAME', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Stockage S3 incomplet: ' + ', '.join(missing))
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.environ['AWS_STORAGE_BUCKET_NAME'],
            'access_key': os.environ['AWS_ACCESS_KEY_ID'],
            'secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'endpoint_url': os.environ.get('AWS_S3_ENDPOINT_URL') or None,
            'region_name': os.environ.get('AWS_S3_REGION_NAME') or None,
            'location': 'new-arrivals',
            'default_acl': 'private',
            'querystring_auth': True,
            'file_overwrite': False,
        },
    }
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', '0') == '1'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'New arrivals <no-reply@example.invalid>')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')

# Production: SMTP credentials must be provided through environment variables.
EMAIL_HOST = os.environ.get('EMAIL_HOST','localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT','587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS','1')=='1'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD','')
FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN','http://localhost:8080')
PASSWORD_RESET_TIMEOUT=3600
REDIS_URL=os.environ.get('REDIS_URL','redis://redis:6379/0')
CELERY_BROKER_URL=REDIS_URL
CELERY_RESULT_BACKEND=REDIS_URL
CELERY_TASK_ALWAYS_EAGER=os.environ.get('CELERY_TASK_ALWAYS_EAGER','0')=='1'
CACHES={'default':{'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':os.environ.get('CACHE_URL','redis://redis:6379/1')}} if os.environ.get('CACHE_URL') else {'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
SENTRY_DSN=os.environ.get('SENTRY_DSN','')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN,traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE','0.05')))

# Internal container health probe must remain reachable over the private HTTP socket.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
