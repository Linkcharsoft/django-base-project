"""Login, logout, refresh and the user's own sessions.

Login, logout and refresh keep dj-rest-auth's URLs and response shapes; what changes is that
every JWT pair belongs to an AuthSession that can be revoked, and that every login attempt is
rate limited and recorded in LoginEvent.
"""

from dj_rest_auth.app_settings import api_settings as rest_auth_settings
from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.views import LoginView as RestAuthLoginView
from dj_rest_auth.views import LogoutView as RestAuthLogoutView
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView

from django_base.base_utils.base_viewsets import BaseGenericViewSet
from security.login_attempts import (
    classify_failure,
    is_rate_limited,
    normalize_email,
    record_login_event,
)
from security.models import AuthSession, LoginEvent
from security.serializers import (
    AuthSessionSerializer,
    DetailSerializer,
    LogoutRequestSerializer,
    SessionRefreshSerializer,
    SessionTokenVerifySerializer,
)
from security.sessions import get_session_id, open_session, revoke_user_sessions

Reason = LoginEvent.Reason
RevokedReason = AuthSession.RevokedReason


class LoginView(RestAuthLoginView):
    """dj-rest-auth's login, rate limited, recorded in LoginEvent and backed by an AuthSession.

    429 when the IP or the email ran out of attempts (``LOGIN_RATE_LIMIT_*``).
    """

    def post(self, request, *args, **kwargs):
        self.request = request
        email = normalize_email(request.data.get("email") or request.data.get("username"))
        if is_rate_limited(request, email):
            record_login_event(request, Reason.THROTTLED, email)
            raise Throttled(wait=settings.LOGIN_RATE_LIMIT_WINDOW.total_seconds())

        self.serializer = self.get_serializer(data=request.data)
        if not self.serializer.is_valid():
            reason, user = classify_failure(email, request.data.get("password"))
            record_login_event(request, reason, email, user=user)
            raise ValidationError(self.serializer.errors)

        self.login()
        record_login_event(request, Reason.OK, email, user=self.user)
        return self.get_response()

    def login(self):
        self.user = self.serializer.validated_data["user"]
        _session, refresh = open_session(self.user, self.request)
        self.refresh_token, self.access_token = refresh, refresh.access_token
        if rest_auth_settings.SESSION_LOGIN:
            self.process_login()


@extend_schema_view(
    get=extend_schema(exclude=True),
    post=extend_schema(request=LogoutRequestSerializer, responses=DetailSerializer),
)
class LogoutView(RestAuthLogoutView):
    """dj-rest-auth's logout, which also revokes the session.

    The session comes from the access token in ``Authorization`` or, if there is none, from
    ``refresh`` in the body.
    """

    def logout(self, request):
        session_id, user_id = None, None
        if hasattr(request.auth, "get"):
            session_id, user_id = get_session_id(request.auth), request.user.pk
        elif refresh := request.data.get("refresh"):
            try:
                token = RefreshToken(refresh)
                session_id, user_id = get_session_id(token), token.get("user_id")
            except TokenError:
                pass
        if session_id is not None:
            AuthSession.objects.filter(pk=session_id, user_id=user_id).revoke(RevokedReason.LOGOUT)
        response = super().logout(request)
        if response.status_code == status.HTTP_200_OK:
            # dj-rest-auth (JWT without blacklist) says the token was *not* invalidated server
            # side; with sessions it was. Same shape, accurate message.
            response.data = {"detail": _("Successfully logged out.")}
        return response


class SessionRefreshView(get_refresh_view()):
    serializer_class = SessionRefreshSerializer


class SessionTokenVerifyView(TokenVerifyView):
    serializer_class = SessionTokenVerifySerializer


class SessionViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, BaseGenericViewSet):
    """The authenticated user's open sessions."""

    permissions = {"default": [IsAuthenticated]}
    serializers = {"default": AuthSessionSerializer}
    pagination_class = None

    def get_queryset(self):
        return AuthSession.objects.valid().filter(user=self.request.user)

    @extend_schema(
        summary="List my open sessions",
        description="Every valid session of the current user. `current` marks the one making the request.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Close one of my sessions",
        description="Revokes the session: its tokens answer 401 from now on. 404 if it is not an open session of the current user.",
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        current = get_session_id(self.request.auth) if hasattr(self.request.auth, "get") else None
        reason = RevokedReason.LOGOUT if instance.pk == current else RevokedReason.CLOSED_BY_USER
        AuthSession.objects.filter(pk=instance.pk).revoke(reason)


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Close all my sessions",
        description="Revokes every session of the current user, the current one included.",
        request=None,
        responses=DetailSerializer,
    )
    def post(self, request):
        revoke_user_sessions(request.user, RevokedReason.LOGOUT_ALL)
        return Response({"detail": _("All sessions closed.")}, status=status.HTTP_200_OK)
