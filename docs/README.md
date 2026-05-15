# `docs/`

Reference documentation for `django-base-project`. Every file is single-concern — read the one you need.

> **AI agents:** start at [`_agent-index.md`](./_agent-index.md). It's a keyword → file:anchor lookup table designed for grep-then-jump navigation.

## By task (what are you trying to do?)

| You want to… | Read |
|---|---|
| Boot the project for the first time | [quickstart.md](./quickstart.md) |
| Understand what lives where | [architecture.md](./architecture.md) |
| See every endpoint the API exposes | [api-contract.md](./api-contract.md) |
| Understand auth flows (login / JWT / recovery / OAuth) | [auth.md](./auth.md) |
| Trace what happens when a request comes in | [request-lifecycle.md](./request-lifecycle.md) |
| Follow project code conventions (BaseModel, mixins, etc.) | [conventions.md](./conventions.md) |
| Learn the build/dev tools (just, ruff, pre-commit, …) | [toolchain.md](./toolchain.md) |
| Look up an env var | [environment.md](./environment.md) |
| Add an endpoint / app / model | [development-guide.md](./development-guide.md) |
| Write or run tests | [testing.md](./testing.md) |
| Start a new project from this base | [deriving-a-project.md](./deriving-a-project.md) |
| Deploy to production | [deployment.md](./deployment.md) |
| Add Celery or WebSockets to the project | [extending/](./extending/) |
| Fix a common error | [troubleshooting.md](./troubleshooting.md) |

## By topic

```
docs/
├── _agent-index.md          ← keyword → file:anchor (for AI agents)
│
├── quickstart.md            ← Setup
├── environment.md           ← Reference: env vars
├── troubleshooting.md       ← Common errors and fixes
│
├── architecture.md          ← How the codebase is shaped
├── request-lifecycle.md     ← Middleware + view dispatch flow
├── api-contract.md          ← Endpoint inventory
├── auth.md                  ← Auth flows
│
├── conventions.md           ← Code patterns (BaseModel, mixins, validators…)
├── toolchain.md             ← Build/dev tools (just, uv, ruff, pre-commit, spectacular)
├── development-guide.md     ← Step-by-step recipes (add endpoint/app/model/…)
├── testing.md               ← Test setup + conventions
│
├── deriving-a-project.md    ← Kickoff guide for new projects forking this base
├── deployment.md            ← Production setup
│
└── extending/               ← Opt-in features removed from the base
    ├── celery.md            ← Add Celery + Redis for background jobs
    ├── websockets.md        ← Add Channels for realtime/WebSockets
    └── global-places.md     ← Add country/state/city data via django-global-places
```

## Conventions for these docs

- **Scope statement at the top of each file.** Every file starts with a one-paragraph "Scope. X. Not covered: Y (see Z)." block so a reader (human or agent) can decide in <5 seconds if they're in the right place.
- **Tables over prose.** Endpoint inventories, env var lists, middleware orders — all tables. Easier to scan, easier to grep.
- **Cross-link with anchors.** When a doc references another concern, use the exact `file.md#anchor` form so a reader (or agent) can jump precisely.
- **Filename ≈ concern.** One concern per file. When a file grows past ~250 lines, split rather than nest sections.
- **Use the `_` prefix for agent-only files.** Currently only `_agent-index.md`. Keeps them visually grouped at the top.

Past audit history (Phase 1–6 cleanup) lives in git — `git log --all --oneline -- audit/` to browse the deleted plan files.

## Updating these docs

Treat them like code: when you change behavior, update the doc in the same PR. If you add a doc, add a row to:

1. The "By task" table above.
2. The tree under "By topic".
3. The relevant section of [`_agent-index.md`](./_agent-index.md).

If you rename an anchor, `grep -r "#old-anchor" docs/` to find references.
