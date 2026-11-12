from django.utils.translation import gettext_lazy as _
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from security.sessions import get_valid_session, touch

SESSION_INVALID_CODE = "session_invalid"


class SessionJWTAuthentication(JWTAuthentication):
    """JWT authentication that also requires the token's session (claim ``sid``) to be valid.

    A revoked or expired session answers 401 right away, even if the access token itself has
    not expired yet. Tokens without ``sid`` are rejected the same way. On success it refreshes
    the session's ``last_used_at`` (at most once a minute).
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        session = get_valid_session(token)
        if session is None:
            # A dict detail is rendered as is, so the body carries the code next to the message.
            raise AuthenticationFailed(
                {"detail": _("Session expired or closed."), "code": SESSION_INVALID_CODE}
            )
        touch(session)
        return user, token


class SessionJWTScheme(SimpleJWTScheme):
    """OpenAPI: same Bearer scheme as simplejwt's (drf-spectacular matches the exact class)."""

    target_class = SessionJWTAuthentication
