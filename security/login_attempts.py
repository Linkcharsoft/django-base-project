"""Login attempts: the rate limit and the LoginEvent log, shared by the API and the admin login.

The limit is counted on LoginEvent itself, so it needs no shared cache (Redis) and holds across
every worker and container. Every attempt counts, the throttled ones too: a client that keeps
hammering while blocked stays blocked. Callers check the limit *before* authenticating and record
the attempt *after*.
"""

import logging

from allauth.account import app_settings as allauth_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from security.client_ip import get_client_ip
from security.models import LoginEvent
from security.sessions import get_user_agent

logger = logging.getLogger(__name__)

EMAIL_MAX_LENGTH = LoginEvent._meta.get_field("email").max_length


def normalize_email(value):
    return str(value or "").strip().lower()[:EMAIL_MAX_LENGTH]


def is_rate_limited(request, email):
    """True when the IP or the email already spent its attempts inside the window."""
    since = timezone.now() - settings.LOGIN_RATE_LIMIT_WINDOW
    recent = LoginEvent.objects.filter(created_at__gte=since)
    ip = get_client_ip(request)
    if ip and recent.filter(ip_address=ip).count() >= settings.LOGIN_RATE_LIMIT_PER_IP:
        return True
    return bool(email) and recent.filter(email=email).count() >= settings.LOGIN_RATE_LIMIT_PER_EMAIL


def find_user(identifier):
    """The account an attempt was aimed at: by email, or by username (the admin form)."""
    if not identifier:
        return None
    return (
        get_user_model()
        .objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        .order_by("-is_active")
        .first()
    )


def classify_failure(identifier, password, source=LoginEvent.Source.API):
    """Why a login was rejected, for support. The response shows the same error either way."""
    if not identifier or not password:
        return LoginEvent.Reason.INVALID, None
    user = find_user(identifier)
    if user is None:
        return LoginEvent.Reason.UNKNOWN_EMAIL, None
    if not user.is_active:
        return LoginEvent.Reason.INACTIVE, user
    if not user.check_password(password):
        return LoginEvent.Reason.BAD_PASSWORD, user
    if source == LoginEvent.Source.ADMIN and not user.is_staff:
        return LoginEvent.Reason.NOT_STAFF, user
    if (
        allauth_settings.EMAIL_VERIFICATION == allauth_settings.EmailVerificationMethod.MANDATORY
        and not user.emailaddress_set.filter(email__iexact=user.email, verified=True).exists()
    ):
        return LoginEvent.Reason.EMAIL_NOT_VERIFIED, user
    return LoginEvent.Reason.INVALID, user


def record_login_event(request, reason, email, user=None, source=LoginEvent.Source.API):
    ip = get_client_ip(request)
    if user is None and reason == LoginEvent.Reason.THROTTLED:
        user = find_user(email)
    event = LoginEvent.objects.create(
        email=email,
        user=user,
        reason=reason,
        source=source,
        ip_address=ip,
        user_agent=get_user_agent(request),
    )
    if not event.success:
        logger.warning("Login rejected (%s, %s) for %r from %s", reason, source, email, ip)
    return event
