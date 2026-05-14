# `docs/`

Reference documentation for this Django base template. Each file is focused on one concern — read whichever you need.

| File | When to read it |
|---|---|
| [quickstart.md](./quickstart.md) | First thing on a new clone. Sets up local dev in ~5 minutes. |
| [architecture.md](./architecture.md) | Folder layout, settings split, middleware stack, optional features. Read after quickstart. |
| [api-contract.md](./api-contract.md) | Endpoint inventory + frontend contract. Read before touching any view or URL. |
| [auth.md](./auth.md) | Login, signup, JWT, password recovery, Google OAuth, permissions, maintenance flag. |
| [conventions.md](./conventions.md) | `BaseModel`, viewset mixins, file uploads, validators, toolchain (justfile, uv, ruff, pre-commit). |
| [deployment.md](./deployment.md) | Production setup: gunicorn, S3, AWS logs, nginx, Sentry, migration flow. |

For the audit history (Phase 1–6 cleanup of this template), see [`../audit/`](../audit/).

## Updating these docs

Treat them like code: when you change behavior, update the doc in the same PR. The audit's `06-backlog.md` items 6.9 and 6.15 were absorbed into this folder — don't recreate them.
