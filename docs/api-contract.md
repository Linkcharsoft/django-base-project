# API contract

Endpoint inventory and frontend contract. The frontend template consumes these — coordinate before breaking.

The canonical schema is generated at runtime by drf-spectacular: `GET /api/schema/` (YAML), or browse it interactively at `/api/schema/swagger-ui/` (Swagger UI) or `/api/schema/redoc/` (Redoc).

## Base URL

- Dev: `http://localhost:8000`
- Production: configured per derived project (see [deployment.md](./deployment.md))

All API paths are mounted under `/api/`. Two exceptions: `/admin/` and `/healthcheck/`.

## `/api/auth/`

Defined in `auth_api/urls.py`.

| Method | Path | View | Notes |
|---|---|---|---|
| POST | `login/` | `dj_rest_auth.LoginView` | Returns JWT (`access`, `refresh`) |
| POST | `logout/` | `dj_rest_auth.LogoutView` | Server-side session terminate |
| GET | `user/` | `dj_rest_auth.UserDetailsView` | Returns `UserSerializer` (id, email, first_name, last_name, profile) |
| POST | `token/verify/` | `simplejwt.TokenVerifyView` | |
| POST | `token/refresh/` | `dj_rest_auth.get_refresh_view()` | |
| POST | `password/change/` | `PasswordChangeViewModify` | Requires `old_password` + `new_password`. Gated by `PASSWORD_CHANGE_BY_EMAIL` (see [auth.md](./auth.md)) |
| POST | `password/recovery/` | `PasswordRecoveryViewSet.recovery_send_mail` | Throttled `5/hour`. Body: `email`, `request_type` (`reset`\|`change`) |
| POST | `password/recovery/check-token/` | `PasswordRecoveryViewSet.recovery_check_token` | Body: `email`, `token` |
| POST | `password/recovery/confirm/` | `PasswordRecoveryViewSet.recovery_confirm` | Body: `email`, `token`, `password` |
| * | `registration/...` | `dj_rest_auth.registration.urls` | Signup, email verify, resend |
| * | `allauth/...` | `allauth.urls` | Allauth views (account confirm, password reset HTML, etc.) |

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
| DELETE | `users/delete-test-users/` | `delete_test_users` | `AllowAny` ⚠ | Returns `204 No Content`. **Open endpoint** — deletes every user with `is_test_user=True`. Kept open intentionally for the frontend E2E suite |

`PUT` is blocked across all viewsets (returns 405) — see `NoPutViewSetMixin` in [conventions.md](./conventions.md#viewset-mixins).

### Response shapes

- **`retrieve`/`update`/default**: `UserSerializer` → `{id, email, first_name, last_name, profile: {is_register_complete}}`. `email` is read-only.
- **`list`**: `UserListSerializer` → `{id, first_name, last_name, profile: {id}}`. Slim payload.
- **`complete_register`**: `UserRegisterSerializer` → `{first_name, last_name, profile}`. `first_name`/`last_name` required.

## `/api/system-status/`

| Method | Path | Notes |
|---|---|---|
| GET | `system-status/is-system-up/` | Returns `{"is_operational": <bool>}`. Always responds (even during maintenance). |

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

To add a scoped throttle to a new viewset, set `throttle_scope = "<scope_name>"` and add the rate to `DEFAULT_THROTTLE_RATES`.

## Breaking change rules

| Change | Severity | Process |
|---|---|---|
| Internal refactor / new permission on admin-only endpoint | 🟢 Safe | Merge |
| New optional response field / new status code | 🟡 Notify frontend | Mention in PR |
| Renamed path / removed field / new required body field / signature change | 🔴 Breaking | Coordinate with frontend before merge |

The OpenAPI schema at `/api/schema/` is the source of truth for the contract. Validate after changes with `just schema-validate`.
