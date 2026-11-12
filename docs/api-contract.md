# API contract

Endpoint inventory and frontend contract. The frontend template consumes these — coordinate before breaking.

The canonical schema is generated at runtime by drf-spectacular: `GET /api/schema/` (YAML), or browse it interactively at `/api/schema/swagger-ui/` (Swagger UI) or `/api/schema/redoc/` (Redoc).

## Base URL

- Dev: `http://localhost:8000`
- Production: configured per derived project (see [deployment.md](./deployment.md))

All API paths are mounted under `/api/`. Two exceptions: `/admin/` and `/healthcheck/`.

## `/api/auth/`

Defined in `auth_api/urls.py`.

> **Schema visibility.** Only the auth paths the frontend actually consumes are published in the OpenAPI schema; the rest of the dj-rest-auth surface (`user/`, `token/verify/`, `password/change/`) is mounted and still functional, but filtered out by [`django_base/openapi.py`](../django_base/openapi.py). The endpoints in the table below stay listed for repo-internal reference. Edit the whitelist in `django_base/openapi.py` when a route needs to become public.

Login, logout, refresh and verify are dj-rest-auth/simplejwt views subclassed in `security/views.py`: same URLs and response shapes, plus revocable sessions and the login-attempt log ([auth.md → sessions](./auth.md#sessions-revocable-jwt)). Any request with a token whose session is revoked or expired answers `401 {"detail": "Session expired or closed.", "code": "session_invalid"}`.

| Method | Path | View | Auth | Notes |
|---|---|---|---|---|
| POST | `login/` | `security.LoginView` | public | Returns `access`, `refresh`, `access_expiration`, `refresh_expiration`, `user`. Opens a session. `429` over the login rate limit ([auth.md](./auth.md#login-attempts-and-rate-limit)) |
| POST | `logout/` | `security.LogoutView` | public | Revokes the session of the `Authorization` access or, without it, of body `refresh`. `200 {"detail": "Successfully logged out."}` |
| POST | `logout-all/` | `security.LogoutAllView` | JWT | Revokes every session of the user, the current one included. `200 {"detail": "All sessions closed."}` |
| GET | `sessions/` | `security.SessionViewSet.list` | JWT | The user's open sessions, **not paginated**: `[{id, created_at, last_used_at, expires_at, ip_address, user_agent, current}]`. `id` is a UUID; `current` marks the one making the request |
| DELETE | `sessions/{id}/` | `security.SessionViewSet.destroy` | JWT | Closes that session (`204`). `404` if it is not an open session of the user |
| GET | `user/` | `dj_rest_auth.UserDetailsView` | JWT | Returns `UserSerializer` (id, email, first_name, last_name, profile) |
| POST | `token/verify/` | `security.SessionTokenVerifyView` | public | Also `401` when the token's session is no longer valid |
| POST | `token/refresh/` | `security.SessionRefreshView` | public | Returns `access`, `access_expiration`. `401` when the session is revoked or expired; the new access keeps the session |
| POST | `password/change/` | `PasswordChangeViewModify` | JWT | Requires `old_password` + `new_password`. Gated by `PASSWORD_CHANGE_BY_EMAIL` (see [auth.md](./auth.md)). Closes the user's other sessions |
| POST | `password/recovery/` | `PasswordRecoveryViewSet.recovery_send_mail` | public | Throttled `5/hour`. Body: `email`, `request_type` (`reset`\|`change`) |
| POST | `password/recovery/check-token/` | `PasswordRecoveryViewSet.recovery_check_token` | public | Body: `email`, `token` |
| POST | `password/recovery/confirm/` | `PasswordRecoveryViewSet.recovery_confirm` | public | Body: `email`, `token`, `password`. Closes every session of the user |
| POST | `registration/...` | `dj_rest_auth.registration.urls` | public | Signup, email verify, resend |

allauth's HTML views (`allauth.urls`) are not mounted: every login goes through the rate limit and the log.

Everything under `/api/` is private (`IsAuthenticated` by default) unless the view declares `AllowAny`. The exact public list is pinned by a test — see [auth.md → permissions](./auth.md#permissions).

Recovery flow detail: [auth.md → password recovery](./auth.md#password-recovery).

## `/api/users/`

Defined in `users/urls.py` (router) and mounted into `base_router` in `django_base/urls.py`.

| Method | Path | Action | Permission | Notes |
|---|---|---|---|---|
| GET | `users/` | `list` | `IsAdminUser` | Excludes users with unverified email |
| GET | `users/{id}/` | `retrieve` | `IsAuthenticated` | `{id}` accepts `me`. Non-admin always sees their own user regardless of id |
| PATCH | `users/{id}/` | `partial_update` | `HasRegisterCompletePermission` | Writable nested `profile` |
| DELETE | `users/{id}/` | `destroy` | `IsAdminUser` | Cannot self-delete (raises 404 if id == self or `me`) |
| PATCH | `users/complete-register/` | `complete_register` | `IsAuthenticated` | Sets `profile.is_register_complete=True`. Returns 400 if already complete |
| PATCH | `users/{id}/toggle-block/` | `toggle_block` | `IsAdminUser` | Body: `is_active` (bool or `"true"`/`"false"`). Cannot self-block |

`PUT` is blocked across all viewsets (returns 405) — see `NoPutViewSetMixin` in [conventions.md](./conventions.md#viewset-mixins). The verb is also stripped from the OpenAPI schema by the preprocessing hook in [`django_base/openapi.py`](../django_base/openapi.py) so consumers cannot accidentally bind to it.

### Response shapes

- **`retrieve`/`update`/default**: `UserSerializer` → `{id, email, first_name, last_name, profile: {is_register_complete}}`. `email` is read-only.
- **`list`**: `UserListSerializer` → `{id, first_name, last_name, profile: {id}}`. Slim payload.
- **`complete_register`**: `UserRegisterSerializer` → `{first_name, last_name, profile}`. `first_name`/`last_name` required.

## `/api/system-status/`

| Method | Path | Notes |
|---|---|---|
| GET | `system-status/is-system-up/` | Public. Returns `{"is_operational": <bool>}`. Always responds (even during maintenance). |

When `SystemStatus.is_operational=False`, **every other request** returns `503 {"error": "The system is under maintenance"}` unless the path is exempt (admin, this endpoint, `/api/schema/`, `/static/`, `/media/`, `/__debug__/`) or the user is a superuser. Exempt paths are configurable via `SYSTEM_STATUS_EXEMPT_PATHS` in settings (see `platform_configurations/middlewares.py`).

## `/healthcheck/`

Plain text `ok`. Bound to both `/healthcheck/` and `/`. Used by load balancers / uptime monitors. Defined in `django_base/middlewares.py` (`HealthCheckMiddleware`).

## Throttling

Globally configured in `REST_FRAMEWORK` (`django_base/settings/custom_settings.py`):

| Scope | Rate |
|---|---|
| `anon` | 60/minute |
| `user` | 300/minute |
| `password_recovery` (the 3 recovery endpoints) | 5/hour |
| `dj_rest_auth` (scope declared by dj-rest-auth's login, logout, registration and password views) | 60/minute |

Without the `dj_rest_auth` rate, `ScopedRateThrottle` raises on those views and they answer 500 (`test_dj_rest_auth_views_have_a_throttle_rate` guards it). The login has its own, stricter limit on top, counted on `LoginEvent` and shared with the admin login: 30/min per IP and 10/min per email ([auth.md](./auth.md#login-attempts-and-rate-limit)).

To add a scoped throttle to a new viewset, set `throttle_scope = "<scope_name>"` and add the rate to `DEFAULT_THROTTLE_RATES`.

## Breaking change rules

| Change | Severity | Process |
|---|---|---|
| Internal refactor / new permission on admin-only endpoint | 🟢 Safe | Merge |
| New optional response field / new status code | 🟡 Notify frontend | Mention in PR |
| Renamed path / removed field / new required body field / signature change | 🔴 Breaking | Coordinate with frontend before merge |

The OpenAPI schema at `/api/schema/` is the source of truth for the contract. Validate after changes with `just schema-validate`.
