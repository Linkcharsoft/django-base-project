from urllib.parse import parse_qs

from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async

from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError
from jwt import decode as jwt_decode


from rest_framework.authtoken.models import Token


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ["/", "/healthcheck/"]:
            return HttpResponse("ok")
        return self.get_response(request)


User = get_user_model()


class JWTAuthMiddleware:
    """Middleware to authenticate user for channels"""

    def __init__(self, app):
        """Initializing the app."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Authenticate the user based on jwt."""
        close_old_connections()
        try:
            token = parse_qs(scope["query_string"].decode("utf8")).get("token", None)[0]

            data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            scope["user"] = await self.get_user(data["user_id"])
        except (
            TypeError,
            KeyError,
            InvalidSignatureError,
            ExpiredSignatureError,
            DecodeError,
        ):
            scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        """Return the user based on user id."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


def JWTAuthMiddlewareStack(app):
    """This function wrap channels authentication stack with JWTAuthMiddleware."""
    return JWTAuthMiddleware(AuthMiddlewareStack(app))


class TokenAuthMiddleware:
    """Middleware to authenticate user for channels"""

    def __init__(self, app):
        """Initializing the app."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Authenticate the user based on jwt."""
        close_old_connections()
        try:
            token = parse_qs(scope["query_string"].decode("utf8")).get("token", None)[0]

            scope["user"] = await self.get_user_by_token(token)
        except Exception:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user_by_token(self, token):
        try:
            token = Token.objects.prefetch_related("user").get(key=token)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()


def TokenAuthMiddlewareStack(app):
    """This function wrap channels authentication stack with JWTAuthMiddleware."""
    return TokenAuthMiddleware(AuthMiddlewareStack(app))
