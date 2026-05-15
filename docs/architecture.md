# Architecture

High-level map of the codebase. Read [quickstart.md](./quickstart.md) first if you haven't booted the project yet.

## Stack

- **Python 3.13** (Dockerfile pinned to `python:3.13-slim`).
- **Django 6.0** + **Django REST Framework 3.17**.
- **PostgreSQL 16** in dev (docker-compose), `psycopg[binary]` driver.
- **Auth**: `dj-rest-auth` + `django-allauth` + `djangorestframework-simplejwt`.
- **OpenAPI docs**: `drf-spectacular` (OpenAPI 3.1), sidecar assets — no CDN.
- **Settings split**: `split-settings` (5 files under `django_base/settings/`).
- **Runtime**: gunicorn + whitenoise in production; Django dev server in `entrypoint-dev.sh`.

## Folder layout

```
.
├── django_base/                # Django project (settings, urls, asgi, wsgi)
│   ├── settings/               # split-settings (5 files, see below)
│   ├── base_utils/             # cross-app utilities (see conventions.md)
│   ├── middlewares.py          # HealthCheckMiddleware
│   ├── storage_backends.py     # S3 public media backend (gated by USE_S3)
│   └── urls.py wsgi.py asgi.py
├── auth_api/                   # Custom auth endpoints (password recovery, Google login, password change)
├── users/                      # User + Profile + TokenRecovery models, viewset, filters, permissions
├── platform_configurations/    # SystemStatus (global maintenance flag) + IsSystemUpMiddleware
├── templates/                  # HTML email templates (allauth + password recovery)
├── locale/                     # i18n .po/.mo files
├── docs/                       # ← this folder
├── Dockerfile docker-compose.yml docker-compose-production.yml
├── entrypoint.sh entrypoint-dev.sh
├── justfile                    # task runner (see conventions.md)
├── .pre-commit-config.yaml     # ruff + django-upgrade hooks (see conventions.md)
├── pyproject.toml              # ruff, pytest, coverage config
└── requirements.txt
```

## Settings split

`django_base/settings/__init__.py` includes five files in this order (later files can reference earlier ones):

| File | What's in it |
|---|---|
| `environment_variables.py` | `django-environ` `.env` parsing — only the raw env vars |
| `django_settings.py` | `BASE_APPS`, `MIDDLEWARE`, `TEMPLATES`, `AUTH_PASSWORD_VALIDATORS`, `LANGUAGE_CODE`, `TIME_ZONE` |
| `custom_settings.py` | `INSTALLED_APPS` assembly, REST/JWT/allauth/CORS, drf-spectacular, Sentry, S3 |
| `db_settings.py` | `DATABASES` dict (engine selected by `DB_ENGINE` env var) |
| `configurations.py` | Project-level constants (`APP_NAME`, `PASSWORD_CHANGE_BY_EMAIL`, `PASSWORD_RECOVERY_*`, `USE_DEBUG_TOOLBAR`) |

To override a constant per environment, set the corresponding env var (if exposed) or fork `configurations.py` in the derived project.

## Middleware stack

Defined in `django_base/settings/django_settings.py`:

```
HealthCheckMiddleware              → /healthcheck/ + /
SecurityMiddleware (Django)
WhiteNoiseMiddleware               → serves /static/
CorsMiddleware                     → uses CORS_ALLOWED_URLS
SessionMiddleware
AuthenticationMiddleware
IsSystemUpMiddleware               → 503 if SystemStatus.is_operational=False (see auth.md)
LocaleMiddleware
CommonMiddleware
CsrfViewMiddleware
MessageMiddleware
XFrameOptionsMiddleware
allauth.account.AccountMiddleware
```

`debug_toolbar.middleware.DebugToolbarMiddleware` is appended only when `USE_DEBUG_TOOLBAR=True` (see `custom_settings.py`).

## URL layout

Mounted in `django_base/urls.py`:

| Prefix | Module | Purpose |
|---|---|---|
| `/admin/` | `django.contrib.admin` | Django admin |
| `/__debug__/` | `debug_toolbar` | Only when `USE_DEBUG_TOOLBAR=True` |
| `/api/schema/` | `drf_spectacular.views` | OpenAPI schema + Swagger UI + Redoc |
| `/api/auth/` | `auth_api.urls` | Login, logout, JWT, password change/recovery, Google OAuth |
| `/api/users/` | `users.urls` router | User CRUD + custom actions |
| `/api/system-status/` | `platform_configurations.urls` router | Global maintenance health check |
| `/healthcheck/`, `/` | `HealthCheckMiddleware` | Plain `ok` text (for load balancers) |

Full endpoint inventory: [api-contract.md](./api-contract.md).

## Apps inventory

| App | Models | Role |
|---|---|---|
| `users` | `User` (custom, extends `AbstractUser`), `Profile`, `TokenRecovery` | Custom user with `is_test_user` flag, 1-to-1 `Profile` with `is_register_complete`, password recovery tokens |
| `auth_api` | _(none)_ | Custom auth views — extends `dj-rest-auth` |
| `platform_configurations` | `SystemStatus` | Global maintenance flag (`pk=1` singleton) |

There is **no** app called `auth/` — that was the original name and was renamed to `auth_api/` to avoid colliding with `django.contrib.auth` (Phase 6 audit, commit `18e568d`).

## Optional features (off by default)

- **Debug Toolbar** (`USE_DEBUG_TOOLBAR=True`): adds `/__debug__/` and the toolbar middleware. Off by default to avoid leaking diagnostic info.
- **S3 media** (`USE_S3=True` env var): switches `STORAGES["default"]` to `PublicMediaStorage` from `storage_backends.py`.
- **Sentry** (`SENTRY_DSN` env var + `IS_PRODUCTION=True`): initialized at the bottom of `custom_settings.py`. If `IS_PRODUCTION=True` but `SENTRY_DSN` is empty, the project logs a warning and continues (does not crash).

## Extending (Celery / WebSockets)

The base intentionally does **not** ship Celery or Channels code/dependencies — they were removed because the placeholders couldn't actually be activated without installing libs and editing several files. Activation guides with full snippets live in [`extending/celery.md`](./extending/celery.md) and [`extending/websockets.md`](./extending/websockets.md).

## Critical files (do not break)

- `platform_configurations/middlewares.py` — `IsSystemUpMiddleware` runs on every request. If it raises, the whole API is down.
- `django_base/urls.py` — single source of URL truth.
- `users/models.py` — `Profile.create_profile` signal hook on `User` `post_save`. Removing this breaks every endpoint that touches `request.user.profile`.
- `entrypoint-dev.sh` / `entrypoint.sh` — owned by docker-compose; if you change them, `chmod +x` is preserved by the Dockerfile.
