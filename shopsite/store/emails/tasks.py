from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from smtplib import SMTPException
import logging

# from smptplib import SMTPException
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, template_name, context, to_email):
    """
    Shared task to send emails with retry on failure
    Retries up to 3 times with a default delay
    of 60 seconds between retries
    """
    try:
        message = render_to_string(template_name, context)
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"Email sent succesfully to {to_email}")
        return f"Email sent to {to_email}"
    except SMTPException as exc:
        logger.warning(f"Send email Task to {to_email} failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise

    except Exception as exc:
        logger.error(f"Error sending email to {to_email}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise
