import string

import random

from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings


def get_random_string(length):
    characters = string.ascii_letters + string.digits
    result_str = "".join(random.choice(characters) for i in range(length))
    return result_str

def get_date_with_timezone(date):
    return timezone.make_aware(date, timezone.get_default_timezone())

def check_required_fields(data, required_fields):
    errors = {}
    for field in required_fields:
        if field not in data:
            errors[field] = (
                _("This field is required"),
                )
    return errors

def check_fields_options(field_name, field_value, options):
    if field_value not in options:
        return {field_name: (
            _("Invalid option"),
            )}

def email_template_sender(
    subject, template_name, context, to_email, from_email=settings.DEFAULT_FROM_EMAIL
):
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=[to_email], from_email=from_email)
    email.content_subtype = "html"
    email.send()
