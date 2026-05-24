# AGENTS.md

Entrypoint for AI coding agents (Claude Code, Codex, Antigravity, Cursor, …) working in this repo.

## Read this first

For **any non-trivial change**, start at [`docs/_agent-index.md`](./docs/_agent-index.md). It's a keyword → `file#anchor` lookup table — grep it with whatever word came to mind and it'll point you at the right doc.

The human-oriented index is [`docs/README.md`](./docs/README.md).

## What this project is

Django 6.0 + DRF base template used as the starting point for Inferencia projects. Postgres 16, JWT + allauth (email/password only — Google OAuth lives in `docs/extending/google-oauth.md`), drf-spectacular, Docker, `just` task runner.

## Ground rules

1. **Follow `docs/conventions.md`.** `BaseModel`, viewset mixins (`permissions = {...}`, `serializers = {...}`), `unique_upload_to`, etc. New code that ignores these patterns will get bounced in review.
2. **PUT is disabled** project-wide via `NoPutViewSetMixin`. Use `PATCH`.
3. **Env vars are parsed in one place** — `django_base/settings/environment_variables.py`. Never read `os.environ` from another settings file. See [`docs/environment.md → adding-a-new-env-var-checklist`](./docs/environment.md#adding-a-new-env-var-checklist).
4. **The base must boot without optional features.** Celery, Channels, S3, Sentry, debug toolbar, places, etc. are opt-in. Activation guides live in [`docs/extending/`](./docs/extending/) — do not inline them in the base.
5. **When you change behavior, update the doc in the same PR.** [`docs/README.md → Updating these docs`](./docs/README.md#updating-these-docs) has the "what changed → what to touch" table. Stale docs are worse than missing docs.
6. **Run `just lint` and `just test` before declaring work done.** `just schema-validate` if you touched a serializer or viewset.

## Common commands

```bash
docker compose up -d # start dev stack
just migrate         # run migrations
just shell           # Django shell_plus
just test            # pytest
just lint            # ruff format + check --fix
just schema-validate # validate drf-spectacular schema
just manage <cmd>    # any manage.py command
just --list          # see every recipe
```

## When in doubt

Grep [`docs/_agent-index.md`](./docs/_agent-index.md). If your question isn't there, the answer probably belongs there once you've found it — add the row in your PR.
