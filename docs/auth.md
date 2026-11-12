# Authentication

How auth works in this template: who you are, how the server knows it, and which flows are wired up. Quick reference for the endpoints: [api-contract.md](./api-contract.md#apiauth).

## Stack

- **`django-allauth`** — account model + email verification. Social providers are opt-in (see [extending/](./extending/)).
- **`dj-rest-auth`** — REST wrappers around allauth (login, logout, password reset, registration).
- **`djangorestframework-simplejwt`** — JWT issuance and validation.

- **`security`** (own app) — revocable sessions behind every JWT pair, the login-attempt log, the login rate limit and the "Security" admin section. See [Sessions](#sessions-revocable-jwt) below.

DRF auth classes — one, JWT only:

```python
"DEFAULT_AUTHENTICATION_CLASSES": ("security.authentication.SessionJWTAuthentication",),
"DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
```

DRF's `TokenAuthentication` / `rest_framework.authtoken` are **not** installed (a non-expiring, non-revocable token per user would bypass the sessions); `REST_AUTH["TOKEN_MODEL"] = None`.

JWT lifetimes (`SIMPLE_JWT` in `custom_settings.py`):

- Access token: 2 days. Revocation does not wait for it to expire: every request checks its session.
- Refresh token: `SESSION_MAX_TTL` (7 days), and its `exp` is pinned to the session's hard cap (`created_at + SESSION_MAX_TTL`).
- Rotation: **not enabled** (refresh returns a new access only, with the same session).

## User model

`users.User` extends `AbstractUser` + `BaseModel` (which provides `created_at`/`updated_at`), with no extra fields.

On `User.post_save` with `created=True`, a `Profile` is auto-created (signal in `users/models.py`).

The data migration `users/migrations/0002_auto_20230504_1107.py` seeds an `admin@admin.com / admin123123` superuser **only when `DEBUG=True`** at migrate time, and creates the matching `allauth.EmailAddress` row with `verified=True, primary=True` so the admin user can log in immediately without email verification.

Account model behaviors (`custom_settings.py`):

```python
ACCOUNT_LOGIN_METHODS = {"email"}        # username is ignored
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ("email*", "password1*")
ACCOUNT_ADAPTER = "users.adapter.CustomAccountAdapter"
```

## Login (email + password)

`POST /api/auth/login/` with `{"email": "...", "password": "..."}` returns:

```json
{
  "access": "...",
  "refresh": "...",
  "access_expiration": "ISO-8601",
  "refresh_expiration": "ISO-8601",
  "user": { ... }   // UserSerializer payload
}
```

Frontend should store `access` and `refresh`. On 401 with `access_expired`, call `POST /api/auth/token/refresh/` with `{"refresh": "..."}` to get a new access token. If the refresh also answers 401, the session is over (expired, logged out, closed from another device or by an admin): send the user to the login screen.

Every login opens an `AuthSession` (see below) and writes a `LoginEvent`. More than `LOGIN_RATE_LIMIT_PER_IP` attempts per minute from one IP, or `LOGIN_RATE_LIMIT_PER_EMAIL` on one email, answer **429**: see [login attempts](#login-attempts-and-rate-limit).

API login does not open a Django session cookie (`REST_AUTH["SESSION_LOGIN"] = False`): the admin is reached only through `/admin/login/`, with its own rate limit and log, and revoking the JWT session leaves nothing behind.

`POST /api/auth/logout/` revokes the session of the access token sent in `Authorization` or, without one, of `{"refresh": "..."}` in the body. `POST /api/auth/logout-all/` revokes every session of the user.

## Signup

`POST /api/auth/registration/` is provided by `dj-rest-auth.registration`. The serializer is `users.serializers.CustomRegisterSerializer`, which:

- Maps `email` → `username` automatically.
- Has a workaround for the `password2` requirement from dj-rest-auth (auto-copies `password1`).

When email verification is not mandatory, registration answers with a JWT pair too; it also belongs to a session (opened by `REST_AUTH["JWT_TOKEN_CLAIMS_SERIALIZER"]`, without IP or user agent since dj-rest-auth does not pass the request). Registration does not write a `LoginEvent`.

allauth's own HTML views (`allauth.urls`) are **not** mounted: they would let anyone log in around the rate limit and the log. allauth only needs the two named routes `dj_rest_auth.registration.urls` already defines (`account_confirm_email`, `account_email_verification_sent`); the confirmation link points at the frontend (`users/adapter.py`).

Email verification is enforced by allauth — derived projects must wire `EMAIL_PROVIDER` (`console` / `aws` / `smtp`) and verify recipients can reach `EMAIL_HOST_USER`.

## Password recovery

3-step flow. All three endpoints are throttled to **5/hour per IP**.

### 1. Request a token

`POST /api/auth/password/recovery/` with `{"email": "...", "request_type": "reset"}` (or `"change"`).

The server:

1. Generates a random token (length depends on `PASSWORD_RECOVERY_TOKEN_TYPE`: 25 chars for `link`, 6 for `code` — see `configurations.py`).
2. Deletes any existing `TokenRecovery` for that user.
3. Creates a fresh `TokenRecovery` row.
4. Sends an email (template at `templates/registration/password_recovery_email.html`) with a link of the form `{FRONT_URL}/recuperar-contrasena/confirmar/{token}/{email}/` (or `cambiar-contrasena/...` if `request_type=change`).

The response is **always** `200 "Email sent"`, even on failure (timing-safe — does not reveal whether the email exists). Failures are logged via `logger.exception`.

### 2. Validate the token

`POST /api/auth/password/recovery/check-token/` with `{"email": "...", "token": "..."}`. Returns 200 if valid, 400 if expired (>30 min) or unknown.

### 3. Confirm new password

`POST /api/auth/password/recovery/confirm/` with `{"email": "...", "token": "...", "password": "<new>"}`. Runs `validate_password` (Django's password validators + custom `UpperValidator` and `SymbolValidator` from `base_utils/base_validators.py`). On success, deletes the `TokenRecovery` row, **closes every session of the user** (`password_reset`) and 200s.

Token lifetime: **30 minutes** (`PASSWORD_RECOVERY_TOKEN_EXPIRE_AT`).

## Password change (authenticated)

`POST /api/auth/password/change/` is gated by the setting `PASSWORD_CHANGE_BY_EMAIL` (default `True`):

- **`True` (default)**: this endpoint returns 400 with `"Only password change by email is allowed"`. The user must use the recovery flow above, with `request_type="change"`.
- **`False`**: the endpoint accepts `{"old_password": "...", "new_password": "..."}` and changes the password in-place. The user's **other** sessions are closed (`password_change`); the one making the request stays open.

See `auth_api/views.py:PasswordChangeViewModify`.

## Social login (Google OAuth)

Not shipped with the base. To add Google OAuth, follow [extending/google-oauth.md](./extending/google-oauth.md) — it covers `allauth.socialaccount`, the `GoogleLogin` view, the `SocialApp` setup in admin, and the `GOOGLE_REDIRECT_URI` env var.

## Permissions

**The API is private by default.** `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`, so a new endpoint answers 401 to anonymous clients unless it declares `AllowAny` explicitly (`permissions = {"default": [AllowAny]}` on a viewset, `permission_classes = [AllowAny]` on a plain view). The whole public surface is pinned by `test_public_endpoints_are_exactly_the_allowed_list` in [`django_base/tests.py`](../django_base/tests.py): making something public means adding it to `PUBLIC_ENDPOINTS` there, on purpose.

Public today: login, logout, token refresh/verify, registration (+ verify/resend email), the three password recovery steps, `/api/system-status/` (+ `is-system-up/`), and the OpenAPI schema/Swagger/Redoc. The admin login (`/admin/login/`) and `/healthcheck/` are not DRF views.

Permission classes in use:

- **`IsAuthenticated`** / **`IsAdminUser`** / **`AllowAny`** (DRF built-ins).
- **`users.permissions.HasRegisterCompletePermission`** — allows access only if `request.user.is_authenticated` AND `request.user.profile.is_register_complete=True`. This is the default for most write actions on `/api/users/`.

Per-viewset permissions use the `permissions = {action: [...]}` pattern — see [conventions.md → ViewSetPermissionMixin](./conventions.md#viewsetpermissionmixin).

## Sessions (revocable JWT)

App `security/`. Every JWT pair belongs to an `AuthSession` (user, IP, user agent, `created_at`, `last_used_at`, `revoked_at`, `revoked_reason`). The refresh and every access derived from it carry its id in the claim **`sid`**.

A session is valid while `revoked_at` is null and `now < min(last_used_at + SESSION_IDLE_TTL, created_at + SESSION_MAX_TTL)`. That is computed when the token is checked (`AuthSession.objects.valid()`); no expiry is stored. `expires_at` on the model is a derived property, for display.

| Setting (`configurations.py`) | Default | Meaning |
|---|---|---|
| `SESSION_IDLE_TTL` | 3 days | Unused for this long → expired |
| `SESSION_MAX_TTL` | 7 days | Hard cap since login, in use or not. Also the refresh lifetime |

`SessionJWTAuthentication` answers **401** `{"detail": "Session expired or closed.", "code": "session_invalid"}` when the token has no `sid` or its session is revoked or expired — right away, even if the access token itself has not expired. On success it bumps `last_used_at`, at most once a minute. The refresh endpoint checks the session before issuing (401 `token_not_valid` otherwise) and keeps the same `sid`; `token/verify/` checks it too.

What closes sessions (`revoked_reason`):

| Event | Sessions closed | Reason |
|---|---|---|
| `POST /api/auth/logout/` | the current one | `logout` |
| `POST /api/auth/logout-all/` | all of the user's | `logout_all` |
| `DELETE /api/auth/sessions/{id}/` | that one | `closed_by_user` (`logout` if it is the current one) |
| Password change (API) | all but the current one | `password_change` |
| Password set any other way (admin form, shell) | all | `password_change` |
| Password recovery confirm | all | `password_reset` |
| `is_active` → `False` (admin, `toggle-block`, shell) | all | `user_deactivated` |
| Admin actions "Close session" / "Close all sessions" | the selected ones | `admin` |
| User deleted | rows deleted (cascade) | — |

The password and deactivation rules live in `security/signals.py` (`pre_save`/`post_save` on the user), so every path that saves the user is covered. A view that changes the password can set the reason and the surviving session with `security.signals.mark_password_change(user, reason=..., keep_session=...)` before saving. An inactive user cannot log in (allauth/ModelBackend) and their old tokens fail too (simplejwt checks `is_active`).

The user lists and closes their own sessions with `GET /api/auth/sessions/`, `DELETE /api/auth/sessions/{id}/` and `POST /api/auth/logout-all/` — see [api-contract.md](./api-contract.md#apiauth).

Anything else that issues JWTs must go through `security.sessions.open_session(user, request)`: a bare `RefreshToken.for_user(user)` has no `sid` and is rejected. dj-rest-auth's own `jwt_encode` (registration, `SocialLoginView` for [Google OAuth](./extending/google-oauth.md)) is already covered by `JWT_TOKEN_CLAIMS_SERIALIZER`. A WebSocket auth middleware ([extending/websockets.md](./extending/websockets.md)) should check the session with `security.sessions.get_valid_session(token)`.

## Login attempts and rate limit

Every attempt on `POST /api/auth/login/` and on the Django admin login (`/admin/login/`, `security/admin_login.py`) writes a `LoginEvent`: email (normalized), user (when the account exists), `reason`, `source` (`api`/`admin`), IP, user agent, timestamp.

Reasons: `ok`, `bad_password`, `unknown_email`, `email_not_verified` (only when allauth verification is mandatory), `inactive`, `throttled`, `not_staff` (admin login only), `invalid` (missing fields). The client always gets the same generic error; the reason is for support.

The rate limit is counted on `LoginEvent` itself — no Redis or shared cache needed, and it holds across workers and containers:

| Setting (`configurations.py`) | Default |
|---|---|
| `LOGIN_RATE_LIMIT_WINDOW` | 1 minute |
| `LOGIN_RATE_LIMIT_PER_IP` | 30 attempts |
| `LOGIN_RATE_LIMIT_PER_EMAIL` | 10 attempts |

The limit is checked **before** authenticating and the attempt is recorded **after**. Every attempt counts, `throttled` ones included (a client that keeps hammering stays blocked), and the API and the admin share the counters. Over the limit: **429** in the API, the login form with an error (status 429) in the admin; both recorded as `throttled`.

### Client IP behind a proxy

`security.client_ip.get_client_ip(request)` reads `X-Forwarded-For` **from the right**, `TRUSTED_PROXY_COUNT` hops in (env var, see [environment.md](./environment.md)). Each trusted proxy appends the address it got the connection from, so that entry is reliable; anything further left was written by the client and can be forged. `0` (default, local dev) ignores the header and uses `REMOTE_ADDR`. A hop that is not a valid IP gives `None`.

| Deploy | Chain | `TRUSTED_PROXY_COUNT` |
|---|---|---|
| Local (docker compose) | none | `0` |
| `base_infra_fargate` | client → ALB (appends) → gunicorn | `1` |
| `base_infra_EC2` | client → Caddy (replaces XFF) → gunicorn | `1` |

A CDN in front (CloudFront, Cloudflare) adds a hop: raise the count **and** make sure the origin only accepts traffic from that CDN, or the extra hop can be forged.

## Admin: "Security" section

All labels are in English through `gettext`, like the rest of the admin; a project that adds a locale translates them with `just messages`.

- **Sessions** — filter by status (active / expired / revoked) and revoke reason, search by email or IP, action "Close session". A revoked row shows the reason on hover; the detail page has every field.
- **Login attempts** — read only (no add, change or delete); filter by reason, source and date; search by email or IP.
- **Summary** — users on alert and the IPs with the most failed logins in the window, linking to the filtered lists.
- **Users** (users app) — columns for open sessions, last use and failed logins in the window (⚠ at the threshold), filter "On alert", sessions inline, action "Close all sessions". To fit at 1280 px the list shows id, email, staff and those three; username, names, active and test-user flags are on the detail page and in the filters.

| Setting (`configurations.py`) | Default | Meaning |
|---|---|---|
| `SECURITY_FAILED_LOGINS_WINDOW` | 7 days | Window for the failure counts |
| `SECURITY_FAILED_LOGINS_ALERT` | 5 | Failures that put a user on alert |

A failure is any `LoginEvent` whose reason is not `ok` (throttled included).

### Purging old records

`python manage.py purge_security_records` deletes login events older than `LOGIN_EVENT_RETENTION` (90 days) and sessions that ended (revoked or expired) more than `AUTH_SESSION_RETENTION` (30 days) ago. Run it daily from cron, or schedule it with Celery Beat: [extending/celery.md](./extending/celery.md#scheduling-the-security-purge).

### Porting to a derived project

1. Copy `security/` and add `"security"` to `MY_APPS`.
2. Copy the "Sessions and login attempts" block of `configurations.py`, and `TRUSTED_PROXY_COUNT` from `environment_variables.py` (+ `.env.example`). Set it in the deploy: 1 behind the ALB or Caddy.
3. In `custom_settings.py`: the `DEFAULT_AUTHENTICATION_CLASSES` / `DEFAULT_PERMISSION_CLASSES` above, `REST_AUTH["JWT_TOKEN_CLAIMS_SERIALIZER"]`, `REST_AUTH["TOKEN_MODEL"] = None`, `REST_AUTH["SESSION_LOGIN"] = False`, `SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] = SESSION_MAX_TTL`, the `"dj_rest_auth"` throttle rate, and drop `rest_framework.authtoken` from `INSTALLED_APPS`.
4. URLs: login / logout / refresh / verify / sessions / logout-all from `security.views` (see `auth_api/urls.py`), `admin/login/` ahead of `admin.site.urls`, and drop `allauth.urls`.
5. Mix `SecurityUserAdminMixin` into the User admin (see `users/admin.py`); call `mark_password_change` from custom password views; anything minting JWTs uses `open_session`.
6. Review every view for `AllowAny` before switching the default to `IsAuthenticated`, and pin the result with the public-endpoints test.
7. Tokens issued before the deploy have no `sid` and answer 401: every user logs in once more after it.
8. **`authtoken_token`**: removing `rest_framework.authtoken` from `INSTALLED_APPS` leaves its table and migration history in the database; Django just stops using them, nothing breaks. Clients sending `Authorization: Token ...` stop working, so find them first (`SELECT user_id, created FROM authtoken_token`). To drop the table, run `python manage.py migrate authtoken zero` **before** removing the app, or `DROP TABLE authtoken_token` afterwards. The template ships no migration for it.

## Global maintenance flag

`SystemStatus.is_operational` (singleton row, pk=1) controls a kill-switch via `IsSystemUpMiddleware`. When `False`:

- All non-exempt paths return `503 {"error": "The system is under maintenance"}`.
- Exempt: `/admin/`, `/api/system-status/`, `/api/schema/`, `/static/`, `/media/`, `/__debug__/`, plus any superuser.
- Configurable via `SYSTEM_STATUS_EXEMPT_PATHS` in settings.

Toggle from `/admin/platform_configurations/systemstatus/` or via the Django shell. Useful during deploys.
