import os
from pathlib import Path
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-demo-key'
DEBUG = True
ALLOWED_HOSTS = ['*']
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.staticfiles']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.middleware.common.CommonMiddleware']
ROOT_URLCONF = 'valaproject.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': []}}]
WSGI_APPLICATION = 'valaproject.wsgi.application'
DATABASES = {'default': dj_database_url.config(default=os.environ.get('DB_URL', 'sqlite:///db.sqlite3'), conn_max_age=600)}
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
