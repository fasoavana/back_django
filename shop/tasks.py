"""Asynchronous mail with synchronous fallback when Redis is intentionally disabled."""
import logging
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from celery import shared_task
logger=logging.getLogger(__name__)

@shared_task(autoretry_for=(ConnectionError,TimeoutError),retry_backoff=True,retry_kwargs={'max_retries':3})
def send_transaction_email(subject,body,recipients):
    return send_mail(subject,body,settings.DEFAULT_FROM_EMAIL,recipients,fail_silently=False)

def queue_email(subject,body,recipients):
    def deliver():
        if getattr(settings,'CELERY_TASK_ALWAYS_EAGER',False):
            try:send_transaction_email(subject,body,recipients)
            except Exception:logger.exception('Envoi email impossible')
        else:
            try:send_transaction_email.delay(subject,body,recipients)
            except Exception:logger.exception('File Celery indisponible: email non envoyé')
    transaction.on_commit(deliver)
