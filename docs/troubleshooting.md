# Troubleshooting

**Scope.** Errors you'll hit during normal dev/ops and how to fix them. Not covered: feature work (see [development-guide.md](./development-guide.md)).

## Setup / boot

### `just: command not found`

`just` isn't installed or isn't on PATH. Install:

- Windows: `winget install Casey.Just` (then restart the shell).
- macOS: `brew install just`.
- Linux: `cargo install just`.

### `just` recipes error with `no such file or directory: sh`

You're on Windows and `set windows-shell` is missing or wrong in `justfile`. Confirm the top of [`justfile`](../justfile) contains:

```
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
```

### `docker compose: command not found` (or `docker-compose` is invoked)

You're on Compose v1. We require **Compose v2** (the `docker compose ...` plugin). Update Docker Desktop, or on Linux install `docker-compose-plugin`.

### `psycopg.OperationalError: connection refused`

The `db` service hasn't finished starting yet, or `.env` `DB_HOST` is wrong.

- For the dockerized DB: `DB_HOST=db` (not `localhost`).
- For a host DB from inside the container: `DB_HOST=host.docker.internal`.

Wait a few seconds after `docker compose up -d`, or `just logs` to confirm Postgres is ready.

### Port 8000 already in use

```bash
docker compose down       # stop the dev stack
# or, find what's holding 8000:
#   Windows: netstat -aon | findstr :8000 → tasklist /FI "PID eq <pid>"
#   macOS/Linux: lsof -i :8000
```

### `ImproperlyConfigured: Set the X environment variable`

A required env var is missing from `.env`. Cross-check with [environment.md → Required](./environment.md#required-the-project-will-not-boot-without-these). The `.env.example` is the canonical template.

## Migrations

### `django.db.utils.ProgrammingError: relation "..." does not exist`

You haven't migrated, or migrations are pending. Run:

```bash
just migrate
```

If the error happens during `migrate` itself: a migration file references a model that another app hasn't migrated yet. Run `just manage migrate --plan` to see the order.

### `No changes detected` but you edited a model

You probably edited the file outside the package, or the app isn't in `INSTALLED_APPS`. Verify:

```bash
just manage check
just manage makemigrations <app_label>
```

### `InconsistentMigrationHistory`

A migration was applied that depends on one that wasn't. Usually happens when checking out an older branch. Fix:

```bash
just manage migrate <app> zero   # roll back the app
just manage migrate              # re-apply in correct order
```

For dev only — don't do this in prod. In prod, fix forward.

## Auth

### Login returns 400 `"E-mail address is not verified"`

allauth blocks unverified accounts. Two fixes:

- **Dev**: log into `/admin/`, open the user's `EmailAddress` row, check `verified`.
- **Dev shortcut**: if you're the superuser, migration `users/0002_auto_20230504_1107` already creates a verified `EmailAddress` for you (when `DEBUG=True` at migrate time).

### Login returns 401 immediately after registration

Same root cause — registration triggers email verification. With `EMAIL_PROVIDER=console`, the verification link prints to the dev server logs (`just logs`). Click it, then retry login.

### `POST /api/auth/password/change/` returns 400 "Only password change by email is allowed"

By design. `PASSWORD_CHANGE_BY_EMAIL=True` (default) forces the recovery flow. See [auth.md → password change](./auth.md#password-change-authenticated). To enable in-app password change, set `PASSWORD_CHANGE_BY_EMAIL=False` in `configurations.py`.

### JWT expired but `/api/auth/token/refresh/` returns 401

Refresh tokens last 5 days. After that, the user must log in again. (Rotation is **not** enabled — see audit backlog 6.11.)

## Maintenance mode

### Every endpoint suddenly returns 503

`SystemStatus.is_operational` is `False`. Flip it back from `/admin/platform_configurations/systemstatus/` (or `just shell` → `SystemStatus.objects.update(is_operational=True)`).

If you can't reach admin either — the path is exempt, double-check your auth (you need to be staff to reach admin). Worst case: bypass via shell.

### `/api/system-status/is-system-up/` returns 503

That endpoint is exempt from the gate — if it 503s, something else (DB down, app crashed) is wrong. Check `just logs`.

## DRF / schema

### `just schema-validate` fails

Most common cause: a project base viewset is missing `serializers["default"]`, or a non-standard viewset is missing a valid serializer source such as `get_serializer_class`. drf-spectacular silently ignores such viewsets; `--fail-on-warn` surfaces it.

Second most common: an `@action` without `@extend_schema` and ambiguous response type. Annotate:

```python
@extend_schema(request=MySerializer, responses={200: MyResponseSerializer})
@action(...)
def my_action(self, request, ...): ...
```

### `PUT /api/users/1/` returns 405

By design. `NoPutViewSetMixin` blocks PUT to force `PATCH` usage. Use `PATCH` from the frontend.

### Endpoint returns 401 with valid JWT

Check that the `Authorization` header is `Bearer <jwt>` (not `Token <jwt>` — `Token` is for the legacy `TokenAuthentication` flow, which expects a different DB-issued key).

## Ruff / pre-commit

### `pre-commit` blocks the commit, fixes are applied

That's the hook working as intended. `git add` the fixed files and re-commit.

### `pre-commit autoupdate` introduced a new lint failure

A new ruff version added a rule. Either fix the code or disable the rule in `pyproject.toml` `[tool.ruff.lint]`. Don't pin ruff back — review and decide per rule.

### `git blame` shows the format commit on every line

You haven't configured the blame skip:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## Tests

### Tests fail with `503 under maintenance`

A prior test set `SystemStatus.is_operational=False`. Use the autouse fixture from [testing.md → Maintenance mode in tests](./testing.md#maintenance-mode-in-tests).

### Tests fail with `Throttled` (429)

The password recovery endpoints throttle to `5/hour`. Use the throttle override fixture from [testing.md → Throttling in tests](./testing.md#throttling-in-tests).

## Production

### Sentry not capturing errors

Both `IS_PRODUCTION=True` AND `SENTRY_DSN=<value>` must be set. Confirm with:

```bash
docker compose exec web python -c "from django.conf import settings; print(settings.IS_PRODUCTION); import sentry_sdk; print(sentry_sdk.Hub.current.client.dsn)"
```

### Static files 404 in production

`collectstatic` didn't run. The production `entrypoint.sh` should call it; if you customized it, verify. Manual fix:

```bash
docker compose -f docker-compose-production.yml exec web python manage.py collectstatic --noinput
```

### Healthcheck returns 200 but app is broken

By design — `HealthCheckMiddleware` runs before everything else, so it stays green during maintenance and most app failures. Use `GET /api/system-status/is-system-up/` for app-level health (it touches the DB).

## When in doubt

```bash
just logs               # tail web container
just shell              # shell_plus (models pre-imported)
just bash               # full bash inside the container
just manage check       # Django system check
just manage diffsettings  # see what your settings actually resolve to
```
