# Environment variables

**Scope.** Every env var the project reads, where it's parsed, and what happens when it's missing. Not covered: where to *store* secrets in production (use your platform's secret manager — see [deployment.md](./deployment.md)).

All vars are parsed in [`django_base/settings/environment_variables.py`](../django_base/settings/environment_variables.py) via `django-environ`, then consumed across the other settings files. The canonical template is [`.env.example`](../.env.example) — copy it to `.env` for local dev.

## Required (the project will not boot without these)

| Var | Type | Used in | Notes |
|---|---|---|---|
| `SECRET_KEY` | str | `django_settings.py` | Django signing key. Generate per environment, never reuse dev secret in prod. |
| `DEBUG` | bool | `django_settings.py` | `True` in dev only. Controls `DEBUG`, debug toolbar wiring, and the `admin@admin.com` auto-create in `entrypoint-dev.sh`. |
| `IS_PRODUCTION` | bool | `custom_settings.py` | Gates Sentry init. Set `True` only in prod. |
| `FRONT_URL` | url | `auth_api/`, password recovery emails | Used to build recovery / verification links. **No trailing slash** in stored value (templates add `/`). |
| `CSRF_TRUSTED_ORIGINS` | csv | `django_settings.py` | Comma-separated origins for CSRF. |
| `ALLOWED_HOSTS` | csv | `django_settings.py` | Comma-separated host headers. |
| `CORS_ALLOWED_URLS` | csv | `custom_settings.py` (CORS) | Origins allowed by `django-cors-headers`. |
| `DB_ENGINE` | enum | `db_settings.py` | One of `sqlite3`, `postgresql`, `mysql`, `oracle`. |
| `DB_USER` `DB_PASSWORD` `DB_HOST` `DB_PORT` `DB_NAME` | str | `db_settings.py` | DB credentials. With dockerized DB, `DB_HOST=db`. With sqlite, the rest are ignored but must be present (any value). |
| `EMAIL_PROVIDER` | enum | `custom_settings.py` | `console` (dev), `smtp`, `aws` (`django_ses.SESBackend`). |
| `EMAIL_HOST` `EMAIL_HOST_USER` `EMAIL_HOST_PASSWORD` `EMAIL_USE_TLS` `EMAIL_PORT` | mixed | `custom_settings.py` | SMTP credentials. Ignored when `EMAIL_PROVIDER=console` or `aws`. |
| `DEFAULT_FROM_EMAIL` | email | `custom_settings.py` | Sender for all outbound mail (password recovery, allauth verification, etc.). |

## Optional (features off by default)

| Var | Default | Enables | Notes |
|---|---|---|---|
| `USE_S3` | `False` | S3 public media via `PublicMediaStorage` | Requires the three `AWS_*` vars below. |
| `AWS_ACCESS_KEY_ID` | `''` | (S3 + SES) | |
| `AWS_SECRET_ACCESS_KEY` | `''` | (S3 + SES) | |
| `AWS_STORAGE_BUCKET_NAME` | `''` | (S3 only) | |
| `BROKER_SERVER` | `redis` | Celery + Channels broker host | Consumed only when the corresponding `USE_*` flag is set in [`configurations.py`](../django_base/settings/configurations.py). |
| `BROKER_SERVER_PORT` | `6379` | (same as above) | |
| `SENTRY_DSN` | `''` | Sentry error reporting | Used only when `IS_PRODUCTION=True`. Missing DSN logs a warning, does **not** crash. |
| `GOOGLE_REDIRECT_URI` | `http://localhost:3000/auth/google/callback` | Google OAuth callback | Google `CLIENT_ID` / `CLIENT_SECRET` are **not** env vars — stored in admin (`SocialApp` model). See [auth.md → Google OAuth](./auth.md#google-oauth). |

## Compile-time flags (not env vars)

Defined in [`django_base/settings/configurations.py`](../django_base/settings/configurations.py). Change by editing the file (and committing) — there's no env-var indirection on purpose, since these change project shape.

| Flag | Default | Meaning |
|---|---|---|
| `APP_NAME` | `"Django Base"` | Appears in email templates and OpenAPI title. |
| `PASSWORD_CHANGE_BY_EMAIL` | `True` | If `True`, `/api/auth/password/change/` is disabled — users must use the recovery flow. See [auth.md](./auth.md#password-change-authenticated). |
| `PASSWORD_RECOVERY_TOKEN_TYPE` | `"link"` | `"link"` (25-char URL token) or `"code"` (6-digit OTP). |
| `PASSWORD_RECOVERY_TOKEN_EXPIRE_AT` | `30` (minutes) | Token TTL. |
| `USE_CELERY` | `False` | Wires `django_base/celery.py`. Requires `BROKER_SERVER`. |
| `USE_WEB_SOCKET` | `False` | Wires Channels + `JWTAuthMiddleware*`. Switches the runtime to ASGI. |
| `USE_DEBUG_TOOLBAR` | `False` | Adds `debug_toolbar` middleware + `/__debug__/`. |

## How resolution works

1. `django-environ` reads `.env` once at import time (`environment_variables.py:env = environ.Env()`).
2. `env.bool("X", default=...)`, `env.str("X")`, etc. coerce types. Missing **required** vars raise `ImproperlyConfigured`.
3. Settings modules import the parsed values from `environment_variables` — no settings file re-reads `os.environ` directly. **Add new vars there**, never inline in another settings file.

## Adding a new env var (checklist)

1. Read it once in `environment_variables.py` with a sensible default.
2. Document it here (table above — keep alphabetical within section).
3. Add the line to `.env.example` with a placeholder value and a comment.
4. Use the parsed name (`from django_base.settings.environment_variables import MY_VAR`) in the consuming settings file.
