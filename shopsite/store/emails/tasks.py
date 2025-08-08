from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string


@shared_task
def send_email_task(subject, template_name, context, to_email):
    """
    Shared task to send emails
    """
    message = render_to_string(template_name, context)
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[to_email],
        fail_silently=False,
    )
