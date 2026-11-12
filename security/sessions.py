"""Opening, checking and closing the AuthSession behind a JWT pair."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from security.client_ip import get_client_ip
from security.models import AuthSession

# Claim carried by the refresh token and copied to every access token derived from it.
SESSION_CLAIM = "sid"
USER_AGENT_MAX_LENGTH = AuthSession._meta.get_field("user_agent").max_length
# `last_used_at` is written at most this often, so authenticated traffic does not mean one
# UPDATE per request.
LAST_USED_WRITE_INTERVAL = timedelta(minutes=1)


def get_user_agent(request):
    return request.headers.get("user-agent", "")[:USER_AGENT_MAX_LENGTH]


def open_session(user, request=None, user_agent=None):
    """Create a session for ``user`` and return ``(session, refresh_token)``.

    Without a request (tokens issued by dj-rest-auth outside the login view, or from the admin)
    the session has no IP; ``user_agent`` lets the caller say where it came from.
    """
    session = AuthSession.objects.create(
        user=user,
        ip_address=get_client_ip(request) if request is not None else None,
        user_agent=get_user_agent(request) if request is not None else (user_agent or ""),
    )
    return session, refresh_for_session(session)


def refresh_for_session(session):
    refresh = RefreshToken.for_user(session.user)
    refresh[SESSION_CLAIM] = str(session.pk)
    # The refresh never outlives the session's hard cap.
    refresh.set_exp(from_time=session.created_at, lifetime=settings.SESSION_MAX_TTL)
    return refresh


def get_session_id(token):
    try:
        return uuid.UUID(str(token.get(SESSION_CLAIM)))
    except ValueError:
        return None


def get_valid_session(token):
    """The valid session a validated token belongs to, or ``None`` (no sid, revoked, expired)."""
    session_id = get_session_id(token)
    if session_id is None:
        return None
    return (
        AuthSession.objects.valid()
        .filter(pk=session_id, user_id=token.get(jwt_settings.USER_ID_CLAIM))
        .first()
    )


def touch(session):
    now = timezone.now()
    if now - session.last_used_at >= LAST_USED_WRITE_INTERVAL:
        AuthSession.objects.filter(pk=session.pk).update(last_used_at=now)
        session.last_used_at = now


def revoke_user_sessions(user, reason, keep=None):
    """Close every open session of ``user`` except ``keep`` (a session id). Returns the count."""
    sessions = AuthSession.objects.filter(user=user)
    if keep is not None:
        sessions = sessions.exclude(pk=keep)
    return sessions.revoke(reason)
