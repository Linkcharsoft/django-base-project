# Toolchain

**Scope.** Tools the project ships with and how to use them. Not covered: code patterns (see [conventions.md](./conventions.md)).

| Tool | Role | Config file |
|---|---|---|
| **Docker + Compose v2** | dev + prod containers | `Dockerfile`, `docker-compose.yml`, `docker-compose-production.yml` |
| **just** | task runner | `justfile` |
| **uv** | Python package installer (inside Docker) | (none — invoked from Dockerfile) |
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
just up           # docker compose up -d
just down         # docker compose down
just logs         # tail web container logs
just shell        # Django shell_plus (auto-imports models)
just bash         # bash inside the web container
just migrate
just makemigrations
just manage <cmd> # any manage.py command (e.g. just manage createsuperuser)
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

Two directives at the top of [`justfile`](../justfile) matter:

- `set dotenv-load := true` — auto-loads `.env`, so recipes can reference `$DB_USER` etc.
- `set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]` — required on Windows; `just` defaults to `sh`, which isn't on Windows PATH.

**Why just, not Makefile / runcommands.py?** See `audit/06-backlog.md` item 6.1. Short version: cross-platform (works in PowerShell), self-documenting (`just --list` shows comments as descriptions), no Python bootstrap required for shell commands.

## uv

Used inside the Dockerfile to install Python dependencies — ~10× faster than `pip install`.

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY requirements.txt ./
RUN uv pip sync --system requirements.txt
```

Locally you don't need uv installed; everything runs in the container. To regenerate `requirements.txt` from `requirements.in`:

```bash
docker compose exec web uv pip compile requirements.in -o requirements.txt
```

`requirements.in` is the source of truth (top-level deps). `requirements.txt` is the locked output (full pinned tree). Commit both.

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

Annotate non-trivial actions with `@extend_schema(request=..., responses=...)`. Every viewset **must** set `serializer_class` or override `get_serializer_class`; otherwise spectacular silently ignores it.

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

Pinned in `Dockerfile`, `requirements.txt`, `docker-compose.yml`.
