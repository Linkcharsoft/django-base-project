from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from security.models import AuthSession, LoginEvent


def purge_security_records(now=None):
    """Delete old login events and sessions that ended long ago. Returns ``(events, sessions)``.

    A session "ended" when it was revoked, went idle or hit its hard cap; it is deleted once
    ``AUTH_SESSION_RETENTION`` has passed since then.
    """
    now = now or timezone.now()
    events, _ = LoginEvent.objects.filter(
        created_at__lt=now - settings.LOGIN_EVENT_RETENTION
    ).delete()
    ended_before = now - settings.AUTH_SESSION_RETENTION
    sessions, _ = AuthSession.objects.filter(
        Q(revoked_at__lt=ended_before)
        | Q(last_used_at__lt=ended_before - settings.SESSION_IDLE_TTL)
        | Q(created_at__lt=ended_before - settings.SESSION_MAX_TTL)
    ).delete()
    return events, sessions


class Command(BaseCommand):
    help = (
        "Delete login events older than LOGIN_EVENT_RETENTION and sessions that ended "
        "(revoked or expired) more than AUTH_SESSION_RETENTION ago."
    )

    def handle(self, *args, **options):
        events, sessions = purge_security_records()
        self.stdout.write(f"Deleted {events} login events and {sessions} sessions.")
