# Request lifecycle

**Scope.** What happens to an HTTP request from the moment it hits Django until the response goes out. Useful when debugging *where* something is happening, or when adding cross-cutting behavior. Not covered: per-endpoint logic (see [api-contract.md](./api-contract.md)).

## The path of a request

```
HTTP request
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ HealthCheckMiddleware                                           │
│ → /healthcheck/ or / → return "ok" 200 (SHORT-CIRCUITS)         │
│ → otherwise pass through                                        │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ SecurityMiddleware  (Django built-in)                           │
│ → HTTPS redirect, HSTS, X-Content-Type-Options                  │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ WhiteNoiseMiddleware                                            │
│ → serves /static/ directly                                      │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CorsMiddleware  (django-cors-headers)                           │
│ → reads CORS_ALLOWED_URLS env var                               │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ SessionMiddleware → AuthenticationMiddleware                    │
│ → request.user is set (AnonymousUser if no session)             │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ IsSystemUpMiddleware  (platform_configurations)                 │
│ → if SystemStatus.is_operational=False AND path not exempt      │
│   AND user is not superuser → 503 "under maintenance"           │
│ → otherwise pass through                                        │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ LocaleMiddleware → CommonMiddleware → CsrfViewMiddleware →      │
│ MessageMiddleware → XFrameOptionsMiddleware                     │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ allauth.account.AccountMiddleware                               │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼  (optional: DebugToolbarMiddleware when USE_DEBUG_TOOLBAR)
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ URL resolution  (django_base/urls.py → app urls.py → router)    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ DRF view dispatch                                               │
│ 1. authentication_classes:                                      │
│      SessionJWTAuthentication (JWT + its session must be valid) │
│      → request.user, request.auth set                           │
│ 2. permission_classes (default IsAuthenticated; viewsets via    │
│    ViewSetPermissionMixin):                                     │
│      lookup permissions[action] or permissions["default"]       │
│      → 401/403 if any fails                                     │
│ 3. throttle_classes (anon 60/min, user 300/min, scoped)         │
│ 4. action method runs                                           │
│      get_serializer_class() → serializers[action]               │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
HTTP response  (middleware unwinds in reverse order)
```

## Where to hook in

| You want to… | Edit… |
|---|---|
| Run code on every request before auth | A new middleware, registered **after** `IsSystemUpMiddleware` if it must be gated by maintenance mode, or **before** it to bypass. |
| Add a global response header | Custom middleware (or `SecurityMiddleware` settings if security-related). |
| Authenticate via a new scheme | A class in `DEFAULT_AUTHENTICATION_CLASSES` ([`custom_settings.py`](../django_base/settings/custom_settings.py)). |
| Restrict an action | The viewset's `permissions = {action: [...]}` dict. See [conventions.md](./conventions.md#viewsetpermissionmixin). |
| Skip the maintenance gate for a path | Add it to `SYSTEM_STATUS_EXEMPT_PATHS` in [`custom_settings.py`](../django_base/settings/custom_settings.py). |
| Skip CSRF on a view | Don't — use JWT auth instead. CSRF only applies to session-authenticated requests. |
| Change throttling for one viewset | `throttle_scope = "name"` on the viewset + add the rate to `DEFAULT_THROTTLE_RATES`. |

## Authentication resolution

One auth class: **`security.authentication.SessionJWTAuthentication`** — `Authorization: Bearer <jwt>` header. On top of simplejwt's checks (signature, expiry, active user) it requires the token's session (claim `sid`) to be valid, and answers 401 otherwise. See [auth.md → sessions](./auth.md#sessions-revocable-jwt). DRF's `TokenAuthentication` is not installed.

Without an `Authorization` header, `request.user` is `AnonymousUser` and the permission classes decide: the default `IsAuthenticated` answers 401, so only views declaring `AllowAny` are reachable.

## Maintenance mode (short-circuit)

`IsSystemUpMiddleware` is the only middleware that can refuse a request based on DB state. The exempt path list is intentionally minimal so that ops keeps access during maintenance:

- `/admin/` (so the on-call can flip the flag back)
- `/api/system-status/` (so the frontend can detect maintenance)
- `/api/schema/` (so the OpenAPI viewer keeps working)
- `/static/`, `/media/`, `/__debug__/`

Superusers also bypass the check. See [auth.md → maintenance flag](./auth.md#global-maintenance-flag).

## Tracing a real request

The fastest way to see this in action:

```bash
just shell
```

```python
from django.test import RequestFactory
from django_base.urls import urlpatterns
factory = RequestFactory()
req = factory.get("/api/users/me/", HTTP_AUTHORIZATION="Bearer <token>")
# Then walk MIDDLEWARE in order — or hit the endpoint with USE_DEBUG_TOOLBAR=True
# and inspect the toolbar's "Timer" + "SQL" + "Signals" panels.
```
