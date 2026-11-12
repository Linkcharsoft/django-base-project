"""Per-user and per-IP security figures for the admin: open sessions and recent failed logins."""

from django.conf import settings
from django.db.models import Count, IntegerField, Max, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from security.models import AuthSession, LoginEvent

FAILED = ~Q(reason=LoginEvent.Reason.OK)
TOP_IPS = 20


def failed_logins_since():
    return timezone.now() - settings.SECURITY_FAILED_LOGINS_WINDOW


def _count(queryset):
    """Correlated COUNT per user, so the two counts do not multiply each other's rows."""
    counted = queryset.filter(user=OuterRef("pk")).values("user").annotate(n=Count("pk"))
    return Coalesce(Subquery(counted.values("n"), output_field=IntegerField()), Value(0))


def annotate_user_security(users):
    """Add ``active_sessions``, ``last_activity_at`` and ``failed_logins`` to a User queryset."""
    last_used = AuthSession.objects.filter(user=OuterRef("pk")).order_by("-last_used_at")
    return users.annotate(
        active_sessions=_count(AuthSession.objects.valid()),
        last_activity_at=Subquery(last_used.values("last_used_at")[:1]),
        failed_logins=_count(
            LoginEvent.objects.filter(FAILED, created_at__gte=failed_logins_since())
        ),
    )


def users_on_alert(users):
    return (
        annotate_user_security(users)
        .filter(failed_logins__gte=settings.SECURITY_FAILED_LOGINS_ALERT)
        .order_by("-failed_logins")
    )


def top_failing_ips(limit=TOP_IPS):
    return (
        LoginEvent.objects.filter(FAILED, created_at__gte=failed_logins_since())
        .exclude(ip_address__isnull=True)
        .values("ip_address")
        .annotate(
            failed=Count("pk"),
            emails=Count("email", distinct=True),
            last_failed_at=Max("created_at"),
        )
        .order_by("-failed", "-last_failed_at")[:limit]
    )
