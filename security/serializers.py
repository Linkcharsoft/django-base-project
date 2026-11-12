from dj_rest_auth.jwt_auth import CookieTokenRefreshSerializer
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenVerifySerializer
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from security.models import AuthSession
from security.sessions import get_session_id, get_valid_session, open_session, touch

SESSION_INVALID_MESSAGE = _("Session expired or closed.")


class SessionTokenClaimsSerializer(TokenObtainPairSerializer):
    """``REST_AUTH["JWT_TOKEN_CLAIMS_SERIALIZER"]``: any pair dj-rest-auth issues opens a session.

    The login view opens its own (with IP and user agent); this covers the other paths, such as
    registration when email verification is not mandatory.
    """

    @classmethod
    def get_token(cls, user):
        _session, refresh = open_session(user)
        return refresh


class SessionRefreshSerializer(CookieTokenRefreshSerializer):
    """Refresh only while the session is valid. The new access keeps the same ``sid``."""

    def validate(self, attrs):
        refresh = RefreshToken(self.extract_refresh_token())
        session = get_valid_session(refresh)
        if session is None:
            raise InvalidToken(SESSION_INVALID_MESSAGE)
        touch(session)
        return super().validate(attrs)


class SessionTokenVerifySerializer(TokenVerifySerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if get_valid_session(UntypedToken(attrs["token"])) is None:
            raise InvalidToken(SESSION_INVALID_MESSAGE)
        return data


class AuthSessionSerializer(serializers.ModelSerializer):
    expires_at = serializers.DateTimeField(read_only=True)
    current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = (
            "id",
            "created_at",
            "last_used_at",
            "expires_at",
            "ip_address",
            "user_agent",
            "current",
        )

    @extend_schema_field(serializers.BooleanField())
    def get_current(self, obj):
        request = self.context.get("request")
        auth = getattr(request, "auth", None)
        return hasattr(auth, "get") and get_session_id(auth) == obj.pk


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=False,
        help_text="Only needed when the access token is not sent (e.g. it already expired).",
    )
