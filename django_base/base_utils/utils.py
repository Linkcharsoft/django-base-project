import random
import string

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone


def get_random_string(length):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def get_default_for_email_template():
    return {
        "banner_url": settings.BASE_EMAILS_BANNER_URL,
        "site_name": settings.APP_NAME,
        "year": timezone.now().year,
    }


def email_template_sender(
    subject,
    template_name,
    context,
    to_email,
    from_email=settings.DEFAULT_FROM_EMAIL,
    attachments=None,
):
    context.update(get_default_for_email_template())
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=[to_email], from_email=from_email)
    email.content_subtype = "html"
    if attachments:
        for attachment in attachments:
            email.attach_file(attachment)
    email.send()
