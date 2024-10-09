import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from django_base.middlewares import JWTAuthMiddlewareStack, TokenAuthMiddlewareStack
from django_base.routing import websocket_urlpatterns
from django_base.settings.configurations import USE_JWT

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()


if USE_JWT:
    MiddlewareStack = JWTAuthMiddlewareStack
else:
    MiddlewareStack = TokenAuthMiddlewareStack


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            MiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
