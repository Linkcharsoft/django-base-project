# django-base-project

Corporate Django 5.2 + DRF template used as a starting point for Linkchar projects. Batteries: JWT auth, allauth + Google OAuth, drf-spectacular (OpenAPI 3.1), Postgres 16, Docker, ruff + pre-commit, justfile.

## Quickstart

```bash
cp .env.example .env       # fill in SECRET_KEY, DB_*, DEFAULT_FROM_EMAIL
just build && just up
just migrate
```

Then open:

- `http://localhost:8000/admin/` — Django admin (`admin@admin.com / admin123123` if `DEBUG=True`)
- `http://localhost:8000/api/schema/swagger-ui/` — API docs

Need more detail? See [`docs/quickstart.md`](./docs/quickstart.md).

## Docs

Project documentation lives in [`docs/`](./docs/). Highlights:

- [`docs/architecture.md`](./docs/architecture.md) — what lives where
- [`docs/api-contract.md`](./docs/api-contract.md) — endpoints + frontend contract
- [`docs/auth.md`](./docs/auth.md) — login / JWT / password recovery / Google OAuth
- [`docs/conventions.md`](./docs/conventions.md) — code patterns + toolchain (justfile, uv, ruff)
- [`docs/deployment.md`](./docs/deployment.md) — production setup

## Common tasks

```bash
just                # list every recipe
just shell          # Django shell_plus
just test           # pytest
just lint           # ruff format + check --fix
just schema-validate
just manage <cmd>   # any manage.py command
```

Full list: `just --list`. See [`docs/conventions.md#justfile`](./docs/conventions.md#justfile) for the why.

## License

Internal. Linkchar.
