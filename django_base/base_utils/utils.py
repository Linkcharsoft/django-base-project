import string

import random

from django.utils import timezone


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