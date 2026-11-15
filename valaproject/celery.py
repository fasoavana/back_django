import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE','valaproject.settings')
app=Celery('new_arrivals')
app.config_from_object('django.conf:settings',namespace='CELERY')
app.autodiscover_tasks()
