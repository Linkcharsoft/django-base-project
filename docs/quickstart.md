# Quickstart

Local dev setup, end to end. Takes ~5 minutes on a machine with Docker and `just` already installed.

## Prerequisites

- **Docker** + **Docker Compose v2** (`docker compose ...`, not the legacy `docker-compose`).
- **just** task runner: `winget install Casey.Just` on Windows, `brew install just` on macOS, `cargo install just` elsewhere. See [toolchain.md](./toolchain.md#justfile) for why we use it.

## 1. Clone and configure env

```bash
git clone <repo-url>
cd django-base-project
cp .env.example .env
```

Open `.env` and fill in at least `SECRET_KEY`, `DB_*`, and `DEFAULT_FROM_EMAIL`. Everything in the `Required` section of `.env.example` must have a value; the `Optional` section can stay empty unless you enable S3 or Sentry.

## 2. Build and start

```bash
docker compose up -d --build
```

This builds the `web` and `db` services and launches them in the background. The `db` service is `postgres:16`. The `web` service runs gunicorn-less dev mode (`entrypoint-dev.sh`), which auto-runs `migrate` and `runserver` on container port `8000`, published locally as port `8001`.

## 3. First migration + superuser

```bash
just migrate
just manage createsuperuser
```

If `DEBUG=True`, migration `users/0002_auto_20230504_1107` automatically creates `admin@admin.com / admin123123` (with a verified `EmailAddress`) for convenience — skip the `createsuperuser` step in that case.

## 4. Verify

| URL | What you should see |
|---|---|
| `http://localhost:8001/admin/` | Django admin login |
| `http://localhost:8001/api/schema/swagger-ui/` | OpenAPI 3.1 docs (drf-spectacular) |
| `http://localhost:8001/api/system-status/is-system-up/` | `{"is_operational": true}` |
| `http://localhost:8001/healthcheck/` | `ok` (plain text) |

If any of these fail, check `just logs` for traces.

## 5. Daily workflow

```bash
just shell           # Django shell_plus (auto-imports models)
just bash            # bash inside the web container
just test            # run the test suite (pytest)
just lint            # ruff format + ruff check --fix
just manage <cmd>    # any manage.py command, e.g. `just manage shell`
just --list          # see every recipe with its description
```

To stop the stack: `docker compose down`. To wipe the database: `docker compose down -v` (destroys the named volume `data/db`).

## Where to go next

- **What lives where:** [architecture.md](./architecture.md)
- **What endpoints exist and what the frontend expects:** [api-contract.md](./api-contract.md)
- **Auth flows (login, password recovery):** [auth.md](./auth.md)
- **Code patterns (BaseModel, viewset permission dict, etc.):** [conventions.md](./conventions.md)
- **Production deployment:** [deployment.md](./deployment.md)
