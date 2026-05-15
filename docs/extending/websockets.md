# Extending: WebSockets (Django Channels)

**Scope.** How to add real-time bidirectional connections (WebSockets) to the project using Django Channels.
**Not covered.** Server-Sent Events (HTTP streaming), background jobs (see [celery.md](./celery.md)).

The base intentionally ships **without** Channels: `consumers.py`, `routing.py`, the `USE_WEB_SOCKET` flag, and the channels-dependent imports in `asgi.py` were removed because they didn't compile without the `channels` lib (which wasn't declared). Follow this guide to add WebSockets when needed.

---

## When you need it

- Live chat, notifications pushed to the browser, presence indicators.
- Server-initiated state updates without polling.

If you only need server → client one-way push, consider **SSE** first — it's simpler (plain HTTP, auto-reconnect built into `EventSource`) and doesn't need ASGI infrastructure.

## Infrastructure prerequisite

A Redis broker for the channel layer (required for multi-process scaling — `InMemoryChannelLayer` is fine for tests but breaks under gunicorn workers).

In the `base-infra` stack, reuse the same Redis as Celery but **separate the DB index** (`/1` for channels, `/0` for Celery).

---

## Step-by-step

### 1. Add the dependencies

```bash
uv add channels channels-redis daphne
just build
```

### 2. Update `django_base/asgi.py`

Replace the current minimal ASGI app with the channels protocol router:

```python
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_base.settings")

django_asgi_app = get_asgi_application()

from django_base.middlewares import JWTAuthMiddlewareStack  # noqa: E402
from django_base.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

> The two `noqa: E402` imports must come **after** `get_asgi_application()` to ensure the AppRegistry is populated before any ORM-touching import is loaded.

### 3. Create `django_base/routing.py`

```python
from django.urls import re_path

from django_base import consumers

websocket_urlpatterns = [
    re_path(r"ws/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
```

### 4. Create `django_base/consumers.py`

The pattern below ships a reusable `CustomAsyncWebsocketConsumer` with DRF-style permission classes, plus an example `ChatConsumer`. Delete the `ChatConsumer` once you have real consumers.

```python
import json

from channels.exceptions import AcceptConnection, DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer


class ConsumerPermission:
    def has_permission(self, scope):
        raise NotImplementedError


class IsAuthenticated(ConsumerPermission):
    message = "User is not authenticated"
    code = 4001

    def has_permission(self, scope):
        user = scope.get("user")
        return user is not None and user.is_authenticated


class AllowAny(ConsumerPermission):
    def has_permission(self, scope):
        return True


class CustomAsyncWebsocketConsumer(AsyncWebsocketConsumer):
    permission_classes = [AllowAny]

    def get_permissions(self):
        return [p() for p in self.permission_classes]

    def check_permissions(self, scope):
        for perm in self.get_permissions():
            if not perm.has_permission(scope):
                raise DenyConnection(getattr(perm, "message", None), getattr(perm, "code", 4000))

    async def websocket_connect(self, message):
        try:
            self.check_permissions(self.scope)
            await self.connect()
        except AcceptConnection:
            await self.accept()
        except DenyConnection as e:
            _, code = e.args
            await self.close(code=code)


# Example consumer — replace with your own
class ChatConsumer(CustomAsyncWebsocketConsumer):
    permission_classes = [IsAuthenticated]

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": data["message"]},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"message": event["message"]}))
```

### 5. Add JWT auth middleware for WS

In `django_base/middlewares.py`, append:

```python
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
from jwt import decode as jwt_decode

User = get_user_model()


class JWTAuthMiddleware:
    """Authenticate channels scope from a `?token=...` query param."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        try:
            token = parse_qs(scope["query_string"].decode("utf8")).get("token", [None])[0]
            data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            scope["user"] = await self.get_user(data["user_id"])
        except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError):
            scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


def JWTAuthMiddlewareStack(app):
    return JWTAuthMiddleware(AuthMiddlewareStack(app))
```

The client connects with `ws://host/ws/<room>/?token=<jwt>`. Don't put JWTs in cookies for WS — the browser sends them on every HTTP request too, and Channels' default auth middleware reads sessions only.

### 6. Settings — channel layer + INSTALLED_APPS

In `django_base/settings/environment_variables.py`:

```python
CHANNELS_REDIS_URL = env("CHANNELS_REDIS_URL", default="redis://redis:6379/1")
```

In `django_base/settings/custom_settings.py`:

```python
from django_base.settings.environment_variables import CHANNELS_REDIS_URL  # add to existing import block

# Channels
THIRD_APPS = ["daphne", "channels"] + THIRD_APPS  # daphne MUST come before django.contrib.staticfiles

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [CHANNELS_REDIS_URL]},
    },
}
```

> `daphne` in `INSTALLED_APPS` overrides Django's `runserver` to serve ASGI. Don't forget this — without it, `just up` still runs WSGI and WebSockets 404.

In `.env.example`:

```bash
# <-------------- Channels -------------->
CHANNELS_REDIS_URL='redis://redis:6379/1'
```

### 7. Switch the entrypoint to ASGI

`entrypoint.sh` currently runs `gunicorn` (WSGI). For production with WebSockets, you need an ASGI server. Two options:

**Option A — Daphne (simplest):**
```sh
daphne -b 0.0.0.0 -p 8000 django_base.asgi:application
```

**Option B — Gunicorn + Uvicorn workers (better for mixed HTTP + WS load):**
```sh
gunicorn -w 4 -k uvicorn.workers.UvicornWorker django_base.asgi:application -b 0.0.0.0:8000
```

For option B, also run `uv add 'uvicorn[standard]'`.

In `docker-compose.yml` (dev), update the `web` service `entrypoint-dev.sh`:

```sh
daphne -b 0.0.0.0 -p 8000 django_base.asgi:application
```

### 8. Add a redis service to compose (if not already there for Celery)

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Validation

1. `just build && just up`
2. Open a Django shell: `from channels.layers import get_channel_layer; layer = get_channel_layer(); await layer.send("test", {"type": "hi"})` — should not error.
3. From the browser dev console:
   ```js
   const ws = new WebSocket("ws://localhost:8000/ws/lobby/?token=<your_jwt>");
   ws.onmessage = (e) => console.log(e.data);
   ws.onopen = () => ws.send(JSON.stringify({message: "hello"}));
   ```
   You should see `{"message": "hello"}` echo back. If the connection closes with code 4001, the JWT is invalid or missing.

## Reverse proxy notes

WebSocket upgrades require the proxy to forward `Upgrade` and `Connection` headers. nginx example:

```nginx
location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;  # match your idle-connection policy
}
```

ALB / Cloudflare also require explicit WS support — check provider docs.

## Production notes

- **Sticky sessions are not required** when using `RedisChannelLayer` — any worker can deliver to any client through the shared channel layer.
- **Scale workers horizontally**, not by adding daphne workers per container. One daphne process can handle thousands of idle WS connections.
- **Idle-connection budget**: most cloud LBs cut idle TCP at 60s. Implement ping/pong (`channels` doesn't do this automatically) or set a heartbeat from the client every 30s.
- **Auth refresh**: WS connections don't auto-refresh JWTs. Either set a short reconnect-on-close policy on the client, or implement a custom message type to swap tokens mid-connection.
