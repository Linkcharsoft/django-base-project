from django.utils import timezone


def get_date_with_timezone(date):
    return timezone.make_aware(date, timezone.get_default_timezone())
