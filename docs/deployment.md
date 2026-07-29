# Deployment

Production deployment notes. The template ships a `docker-compose-production.yml` and an `entrypoint.sh` aimed at containerized deploys behind a reverse proxy.

## Production image

Built from the same `Dockerfile` as dev (single-stage, `python:3.14-slim-bookworm`). Notable steps:

1. Installs `postgresql-client-16` for `dumps`/`psql` access from inside the container.
2. Copies `uv` from the official Astral image and runs `uv sync --frozen --no-dev --no-install-project` against `pyproject.toml` + `uv.lock`. The venv lands at `/opt/venv` and is on `PATH`. Dev deps (`ruff`, `pytest*`) are **not** installed in prod images. To opt them in, pass `--build-arg INSTALL_DEV=true`.
3. Copies the project and `chmod +x` both entrypoints.

Production command (in `docker-compose-production.yml`):

```yaml
command: gunicorn --bind 0.0.0.0:8000 --pythonpath code django_base.wsgi:application --workers=4
```

The dev entrypoint (`entrypoint-dev.sh`) is **not** used in production.

## Environment

`IS_PRODUCTION=True` activates the Sentry block in `custom_settings.py`. If `SENTRY_DSN` is also set, `sentry_sdk.init` runs with `traces_sample_rate=1.0` and `profiles_sample_rate=1.0`. If `SENTRY_DSN` is missing, the project logs a warning and continues (does not crash) — added in Phase 1 of the audit.

`DEBUG` must be `False`. Migration `users/0002_auto_20230504_1107` seeds `admin@admin.com` only when `DEBUG=True` at migrate time, so in production that account never exists.

## Static and media

- **Static files**: `whitenoise.middleware.WhiteNoiseMiddleware` serves `/static/` directly from the app container. `collectstatic` runs in `entrypoint.sh`.
- **Media files**:
  - Default: local filesystem at `MEDIA_ROOT = BASE_DIR / "media"`. Use a Docker volume to persist between deploys.
  - With `USE_S3=True`: switches to `django_base.storage_backends.PublicMediaStorage` (subclass of `S3Boto3Storage`). Requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` env vars. Files end up at `https://<bucket>.s3.amazonaws.com/media/...`.

## Reverse proxy (nginx)

The production compose file does not ship an nginx service. Add one when you have a derived project:

```yaml
nginx:
  build: nginx
  restart: always
  volumes:
    - static_volume:/code/static
    - media_volume:/code/media
  ports:
    - "80:80"
  depends_on:
    - web
```

`static_volume` and `media_volume` are already defined as named volumes in `docker-compose-production.yml`. Mount them read-only in nginx and serve directly.

## AWS CloudWatch logs

Attach a `logging` block to the `web` service when running on ECS:

```yaml
web:
  logging:
    driver: awslogs
    options:
      awslogs-group: <log-group-name>
      awslogs-region: us-east-1
      awslogs-stream-prefix: web
```

## Database

`docker-compose-production.yml` does **not** include a `db` service — production deployments are expected to use a managed Postgres (RDS, Cloud SQL, Supabase, etc.). Point `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` at the managed instance.

If you do want a self-hosted Postgres in production, copy the `db` service from `docker-compose.yml` and mount a persistent volume.

## Email

Set `EMAIL_PROVIDER` to `aws` (uses `django_ses.SESBackend`) or `smtp`. The `console` provider is for development only — it prints emails to stdout.

For AWS SES, provision the verified domain/sender in the AWS console and grant the IAM role/credentials `ses:SendEmail` permission.

## Healthcheck

Point your load balancer / orchestrator at `GET /healthcheck/` (or `GET /`). Both return `200 ok` from `HealthCheckMiddleware`, bypassing every other middleware including `IsSystemUpMiddleware`. This means **the healthcheck stays green even when the maintenance flag is on** — by design, so the LB doesn't kill the container during planned maintenance.

A second, more meaningful health endpoint is `GET /api/system-status/is-system-up/`, which returns `{"is_operational": <bool>}` from the DB. Use it for app-level health (not LB health).

## Maintenance mode

Set `SystemStatus.is_operational = False` from `/admin/platform_configurations/systemstatus/` or the shell:

```python
from platform_configurations.models import SystemStatus
SystemStatus.objects.update(is_operational=False)
```

Every API request except exempt paths starts returning `503 {"error": "The system is under maintenance"}`. Reverse with the same admin page. See [auth.md → maintenance flag](./auth.md#global-maintenance-flag).

## Migration deploy flow

The recommended order in production:

```bash
just manage migrate --plan       # preview pending migrations
just manage migrate              # apply
just manage collectstatic --noinput   # if not in entrypoint
```

For zero-downtime deploys, plan migrations to be backwards-compatible with the previous app version (no destructive column drops in the same release as the code change).
