import string

import random

from django.utils import timezone
from django.conf import settings

from django_base.base_utils.base_models import (
    AbstactCountry,
    AbstactExpandedCountry,
    AbstractState,
    AbstractCity
)


def get_random_string(length):
    characters = string.ascii_letters + string.digits
    result_str = "".join(random.choice(characters) for i in range(length))
    return result_str

def get_date_with_timezone(date):
    return timezone.make_aware(date, timezone.get_default_timezone())

def check_required_fields(data, required_fields):
    errors = []
    for field in required_fields:
        if not field in data or not data.get(field):
            errors.append(f"{field} is required")
    return errors

def get_abstract_country_model():
    return AbstactExpandedCountry if settings.INCLUDE_EXPANDED_COUNTRY else AbstactCountry

def get_abstract_state_model():
    return AbstractState if not settings.LOCATION_SCOPE == 'country' else None

def get_abstract_city_model():
    return AbstractCity if settings.LOCATION_SCOPE == 'city' else None

def email_template_sender(
    subject, template_name, context, to_email, from_email=settings.DEFAULT_FROM_EMAIL
):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage

    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=[to_email], from_email=from_email)
    email.content_subtype = "html"
    email.send()
