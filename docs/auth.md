# Authentication

How auth works in this template: who you are, how the server knows it, and which flows are wired up. Quick reference for the endpoints: [api-contract.md](./api-contract.md#apiauth).

## Stack

- **`django-allauth`** — account model + email verification + social providers (Google here).
- **`dj-rest-auth`** — REST wrappers around allauth (login, logout, password reset, registration).
- **`djangorestframework-simplejwt`** — JWT issuance and validation.

DRF auth classes (order matters, both active globally):

```python
"DEFAULT_AUTHENTICATION_CLASSES": (
    "rest_framework.authentication.TokenAuthentication",
    "dj_rest_auth.jwt_auth.JWTAuthentication",
)
```

JWT lifetimes (`SIMPLE_JWT` in `custom_settings.py`):

- Access token: 2 days
- Refresh token: 5 days
- Rotation: **not enabled** (refresh returns a new access only). See backlog item 6.11 if rotation is needed.

## User model

`users.User` extends `AbstractUser` + `BaseModel` (which provides `created_at`/`updated_at`). Adds:

- `is_test_user: bool` — flag used by the open `DELETE /api/users/delete-test-users/` endpoint to wipe E2E fixtures.

On `User.post_save` with `created=True`, a `Profile` is auto-created (signal in `users/models.py`).

The data migration `users/migrations/0002_auto_20230504_1107.py` seeds an `admin@admin.com / admin123123` superuser **only when `DEBUG=True`** at migrate time, and creates the matching `allauth.EmailAddress` row with `verified=True, primary=True` so the admin user can log in immediately without email verification.

Account model behaviors (`custom_settings.py`):

```python
ACCOUNT_LOGIN_METHODS = {"email"}        # username is ignored
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ("email*", "password1*", "is_test_user")
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

Frontend should store `access` and `refresh`. On 401 with `access_expired`, call `POST /api/auth/token/refresh/` with `{"refresh": "..."}` to get a new access token.

## Signup

`POST /api/auth/registration/` is provided by `dj-rest-auth.registration`. The serializer is `users.serializers.CustomRegisterSerializer`, which:

- Maps `email` → `username` automatically.
- Accepts `is_test_user` (defaults to `False`).
- Has a workaround for the `password2` requirement from dj-rest-auth (auto-copies `password1`).

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

`POST /api/auth/password/recovery/confirm/` with `{"email": "...", "token": "...", "password": "<new>"}`. Runs `validate_password` (Django's password validators + custom `UpperValidator` and `SymbolValidator` from `base_utils/base_validators.py`). On success, deletes the `TokenRecovery` row and 200s.

Token lifetime: **30 minutes** (`PASSWORD_RECOVERY_TOKEN_EXPIRE_AT`).

## Password change (authenticated)

`POST /api/auth/password/change/` is gated by the setting `PASSWORD_CHANGE_BY_EMAIL` (default `True`):

- **`True` (default)**: this endpoint returns 400 with `"Only password change by email is allowed"`. The user must use the recovery flow above, with `request_type="change"`.
- **`False`**: the endpoint accepts `{"old_password": "...", "new_password": "..."}` and changes the password in-place.

See `auth_api/views.py:PasswordChangeViewModify`.

## Google OAuth

`POST /api/auth/dj-rest-auth/google/` with `{"access_token": "<from-google>", ...}` triggers `auth_api.views.GoogleLogin` (a `SocialLoginView`). The callback URL is `settings.GOOGLE_REDIRECT_URI` (env var).

Credentials (`CLIENT_ID`, `CLIENT_SECRET`) are **not** env vars — they're stored in Django admin via the `SocialApp` model (allauth's standard). On a fresh project:

1. Go to `/admin/socialaccount/socialapp/`.
2. Add a `SocialApp` with provider=Google, client id + secret from Google Cloud Console.
3. Attach `Site (example.com)` to it (or create a new Site matching your domain).

`SOCIALACCOUNT_PROVIDERS["google"]` in `custom_settings.py` requests scopes `profile`, `email`, `openid` and `access_type=offline` (refresh tokens).

## Permissions

Two permission classes ship in the template:

- **`IsAuthenticated`** / **`IsAdminUser`** (DRF built-ins).
- **`users.permissions.HasRegisterCompletePermission`** — allows access only if `request.user.is_authenticated` AND `request.user.profile.is_register_complete=True`. This is the default for most write actions on `/api/users/`.

Per-viewset permissions use the `permissions = {action: [...]}` pattern — see [conventions.md → ViewSetPermissionMixin](./conventions.md#viewsetpermissionmixin).

## Global maintenance flag

`SystemStatus.is_operational` (singleton row, pk=1) controls a kill-switch via `IsSystemUpMiddleware`. When `False`:

- All non-exempt paths return `503 {"error": "The system is under maintenance"}`.
- Exempt: `/admin/`, `/api/system-status/`, `/api/schema/`, `/static/`, `/media/`, `/__debug__/`, plus any superuser.
- Configurable via `SYSTEM_STATUS_EXEMPT_PATHS` in settings.

Toggle from `/admin/platform_configurations/systemstatus/` or via the Django shell. Useful during deploys.
