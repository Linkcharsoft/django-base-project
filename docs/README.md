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
    ├── global-places.md     ← Add country/state/city data via django-global-places
    └── google-oauth.md      ← Add Google social login (allauth + dj-rest-auth)
```

## Conventions for these docs

- **Scope statement at the top of each file.** Every file starts with a one-paragraph "Scope. X. Not covered: Y (see Z)." block so a reader (human or agent) can decide in <5 seconds if they're in the right place.
- **Tables over prose.** Endpoint inventories, env var lists, middleware orders — all tables. Easier to scan, easier to grep.
- **Cross-link with anchors.** When a doc references another concern, use the exact `file.md#anchor` form so a reader (or agent) can jump precisely.
- **Filename ≈ concern.** One concern per file. When a file grows past ~250 lines, split rather than nest sections.
- **Use the `_` prefix for agent-only files.** Currently only `_agent-index.md`. Keeps them visually grouped at the top.

Past audit history (Phase 1–6 cleanup) lives in git — `git log --all --oneline -- audit/` to browse the deleted plan files.

## Updating these docs

Treat docs like code: when you change behavior, update the doc in the **same PR**. Stale docs are worse than missing docs — an agent that trusts a wrong table will produce wrong code.

### What changed → what to touch

| If you changed… | Update |
|---|---|
| An endpoint (added / removed / changed method or payload) | [api-contract.md](./api-contract.md) + [_agent-index.md](./_agent-index.md) (API contract section) |
| An env var (added / renamed / removed / changed default) | [environment.md](./environment.md) — follow its [adding-a-new-env-var checklist](./environment.md#adding-a-new-env-var-checklist) — + [_agent-index.md](./_agent-index.md) |
| A new Django app | [architecture.md](./architecture.md) (folder layout + apps inventory) + [_agent-index.md](./_agent-index.md) |
| Middleware (added / reordered) | [architecture.md → middleware stack](./architecture.md#middleware-stack) + [request-lifecycle.md](./request-lifecycle.md) |
| A URL mount under `/` | [architecture.md → URL layout](./architecture.md#url-layout) + [api-contract.md](./api-contract.md) if under `/api/` |
| Auth flow (login / JWT / recovery / OAuth) | [auth.md](./auth.md) + [api-contract.md](./api-contract.md) if endpoints changed |
| A code convention (BaseModel, mixin, validator) | [conventions.md](./conventions.md) |
| A new just recipe / tool config | [toolchain.md](./toolchain.md) + [_agent-index.md](./_agent-index.md) |
| Deployment surface (Dockerfile, entrypoint, gunicorn config) | [deployment.md](./deployment.md) |
| An opt-in feature (Celery, Channels, places, …) | the relevant file under [extending/](./extending/) — do **not** add it to the base docs |

### Adding a new doc file

1. Filename ≈ concern. One concern per file. If it grows past ~250 lines, split rather than nest.
2. Start with a scope statement so a reader (or agent) can decide in <5s if they're in the right file:
   ```markdown
   # Title

   **Scope.** What this file covers in one sentence. Not covered: X (see [other-file.md](./other-file.md)).
   ```
3. Wire it into navigation — **all three** are required, otherwise the doc is unreachable for agents:
   - A row in the "By task" table at the top of this README.
   - A line in the "By topic" tree.
   - Rows in the relevant section(s) of [`_agent-index.md`](./_agent-index.md) — see rules below.
4. Opt-in / off-by-default features go in [extending/](./extending/), not the root. The base must boot without them.

### Writing rows for `_agent-index.md`

The index is keyword → `file#anchor`. An agent finds the right doc by grepping this file with whatever word came to mind, so:

- **List synonyms** in the `Keywords` column, comma-separated. Include the exact symbol (`USE_S3`, `/api/users/`), the generic concept (`feature flag`, `user endpoint`), and likely typos / casual phrasings (`env var`, `environment variable`, `.env`).
- **Always link to a specific anchor**, not just the file, when the file has sections: `file.md#anchor` beats `file.md`.
- **Anchor format** is GitHub-Markdown's auto-slug: lowercase, spaces → `-`, punctuation dropped. A heading `## Adding a new env var (checklist)` becomes `#adding-a-new-env-var-checklist`.
- Put the row under the section it conceptually belongs to (Setup, Architecture, API contract, …). Add a new section if none fits.

### Renaming / removing

- Renaming an anchor: `grep -rn "#old-anchor" docs/` and update every hit, including `_agent-index.md`.
- Removing a doc: also remove its row from this README's "By task" table, the "By topic" tree, and every row in `_agent-index.md` that points at it.
- Renaming a file: same as above, plus update cross-references with `grep -rn "old-name.md" docs/`.

### Tone

- Tables over prose. Endpoint inventories, env vars, middleware order — all tables.
- Short scope statement, no marketing language, no "this document describes…" preamble.
- Cross-link liberally with anchors. If a concern lives elsewhere, point there instead of duplicating.
