# Toolchain

**Scope.** Tools the project ships with and how to use them. Not covered: code patterns (see [conventions.md](./conventions.md)).

| Tool | Role | Config file |
|---|---|---|
| **Docker + Compose v2** | dev + prod containers | `Dockerfile`, `docker-compose.yml`, `docker-compose-production.yml` |
| **just** | task runner | `justfile` |
| **uv** | Python package manager (lock + sync, host and container) | `pyproject.toml`, `uv.lock` |
| **ruff** | linter + formatter | `pyproject.toml` `[tool.ruff]` |
| **pre-commit** | git hooks | `.pre-commit-config.yaml` |
| **pytest + pytest-django** | tests | `pyproject.toml` `[tool.pytest.ini_options]` |
| **django-upgrade** | auto-upgrade Django patterns | `.pre-commit-config.yaml` |
| **drf-spectacular** | OpenAPI 3.1 schema | `custom_settings.py` `SPECTACULAR_SETTINGS` |

## justfile

Task runner. Every common operation goes through `just`, including operations inside the container.

Install:
- **Windows**: `winget install Casey.Just`
- **macOS**: `brew install just`
- **Linux**: `cargo install just` (or your distro's package manager)

```bash
just              # list every recipe (this is also `just --list`)
just logs         # tail web container logs
just shell        # Django shell_plus (auto-imports models)
just bash         # bash inside the web container
just migrate
just makemigrations
just manage <cmd> # any manage.py command (e.g. just manage createsuperuser)
just seed         # demo data for frontend/manual testing (idempotent, DEBUG=True only)
just test         # pytest in the web container
just coverage     # pytest --cov, HTML report
just lint         # ruff format + ruff check --fix
just schema-validate  # drf-spectacular --validate --fail-on-warn
just messages         # extract i18n strings to .po
just compilemessages  # build .mo
just psql             # psql against the dockerized DB
just db-bash          # bash inside the postgres container
just db-restore <dump.sql>  # drop schema + restore from SQL dump
```

Docker and uv aren't wrapped — call them directly: `docker compose up -d`, `docker compose down`, `docker compose build`, `uv add <pkg>`, `uv lock`, `docker compose exec web uv sync --frozen`.

Two directives at the top of [`justfile`](../justfile) matter:

- `set dotenv-load := true` — auto-loads `.env`, so recipes can reference `$DB_USER` etc.
- `set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]` — required on Windows; `just` defaults to `sh`, which isn't on Windows PATH.

**Why just, not Makefile / runcommands.py?** See `audit/06-backlog.md` item 6.1. Short version: cross-platform (works in PowerShell), self-documenting (`just --list` shows comments as descriptions), no Python bootstrap required for shell commands.

## uv

Python package manager. `pyproject.toml` is the source of truth for declared dependencies; `uv.lock` is the resolved, hash-pinned dependency tree. **Both are committed.**

### Layout

- `[project.dependencies]` in `pyproject.toml` → runtime deps (installed in prod).
- `[dependency-groups].dev` in `pyproject.toml` → dev-only deps (`ruff`, `pytest-cov`, `pytest-django`). Not installed in prod.
- `uv.lock` → resolved tree (do not edit by hand).

### Dockerfile

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --frozen --no-install-project; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi
```

The venv lands at `/opt/venv` (outside `/code`) so the dev bind mount (`.:/code`) doesn't shadow it. `ENV PATH="/opt/venv/bin:$PATH"` makes `python`, `gunicorn`, `pytest`, `ruff` resolve to the venv.

The `INSTALL_DEV` build arg is set to `"true"` in `docker-compose.yml` (dev) and left at its default `"false"` in `docker-compose-production.yml`.

### Workflow

| Action | Command |
|---|---|
| Add a runtime dep | `uv add <pkg>` (on host) |
| Add a dev dep | `uv add --dev <pkg>` |
| Re-resolve after editing `pyproject.toml` by hand | `uv lock` |
| Apply lock to the running container venv | `docker compose exec web uv sync --frozen` |
| Rebuild image with new deps | `docker compose up -d --build` |

`uv lock` runs on the host (no Docker needed). The lockfile is platform-independent — commit it and CI/prod will install the exact same tree.

### Why not `requirements.txt`?

Old setup used `requirements.in` + `requirements.txt` driven by `uv pip compile` / `uv pip sync`. Migrated to uv-native (`pyproject.toml` + `uv.lock`) because:

- Single source of truth (PEP 621), no parallel files.
- Real lockfile with hashes and cross-platform resolution markers.
- Built-in dev/prod separation via dependency groups — prod image no longer ships `pytest`/`ruff`.
- `uv sync` is faster than `uv pip sync` because it doesn't re-resolve.

## ruff

Lint + format in one binary. Replaces black + isort + flake8. Configured in `pyproject.toml`.

```bash
just lint                                  # format + check --fix
docker compose exec web ruff check .       # check only
docker compose exec web ruff format .      # format only
```

The initial mass-format pass is recorded in [`.git-blame-ignore-revs`](../.git-blame-ignore-revs) — `git blame` will skip it automatically if you configure:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## pre-commit

Git hooks. Install once after cloning:

```bash
pip install pre-commit  # or pipx, or `brew install pre-commit`
pre-commit install
```

Active hooks ([`.pre-commit-config.yaml`](../.pre-commit-config.yaml)):

- **`pre-commit-hooks` v5.0.0** — trailing whitespace, end-of-file fixer, YAML/TOML syntax, merge-conflict markers, large-file guard, `debug-statement` guard (catches stray `breakpoint()` / `pdb.set_trace()`).
- **`ruff-pre-commit` v0.8.0** — runs `ruff` + `ruff-format` on staged files.
- **`django-upgrade` 1.30.0** — auto-rewrites old Django patterns to `--target-version 5.2`.

Bump hook versions periodically: `pre-commit autoupdate`. Review the diff — new ruff versions can introduce new lint rules that fail builds.

## drf-spectacular

Generates the OpenAPI 3.1 schema at runtime. The frontend depends on this schema being accurate.

```bash
just schema-validate     # fails on warnings — run before releases
docker compose exec web python manage.py spectacular --file schema.yaml
```

Annotate non-trivial actions with `@extend_schema(request=..., responses=...)`. Project base viewsets expose serializers through the `serializers = {"default": Serializer, ...}` dict; every viewset must define a non-`None` `"default"` entry, plus per-action entries when the API shape differs. Do **not** also set `serializer_class` on those viewsets.

Browse interactively: `/api/schema/swagger-ui/` or `/api/schema/redoc/`.

## Versions (as of 2026-05-15)

| | Version |
|---|---|
| Python | 3.13 |
| Django | 6.0.5 |
| DRF | 3.17.1 |
| PostgreSQL | 16 |
| ruff | 0.8.x |
| just | 1.36+ |

> `django-upgrade` `--target-version` is pinned at `5.2` in `.pre-commit-config.yaml`. Bump it deliberately when you want the hook to rewrite to 6.x patterns.

Pinned in `Dockerfile`, `pyproject.toml` / `uv.lock`, `docker-compose.yml`.
