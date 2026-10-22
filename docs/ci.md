# CI & dependency updates

**Scope.** What runs automatically on every pull request, and how dependency bumps reach the repo. Not covered: how to write tests ([testing.md](./testing.md)), local tooling ([toolchain.md](./toolchain.md)).

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every PR and on pushes to `main`. Two jobs, in parallel (plus a third, `dependabot`, that only runs on Dependabot PRs — see [automated review](#automated-review)):

| Job | Steps |
|---|---|
| **Lint** | `uv lock --check` · `ruff check` · `ruff format --check` |
| **Tests** | `manage.py check` · `makemigrations --check` · `migrate` · `pytest --cov` · seed idempotency · schema validation |

CI does **not** use Docker. It installs with `uv sync` directly on the runner and talks to a `postgres:16` service container — same Postgres as local, no SQLite fallback.

### Steps worth knowing about

- **`uv lock --check`** — fails when `uv.lock` and `pyproject.toml` disagree. Everything else installs with `--frozen`, so without this check the failure surfaces later as a confusing `uv sync` error inside the Docker build.
- **`makemigrations --check --dry-run`** — fails when a model changed and its migration wasn't generated. That combination passes review and breaks on deploy, not in the suite.
- **Seed idempotency** — runs `manage.py seed` twice and asserts the row counts didn't move. The frontend develops against `just seed`, so a seed that duplicates rows is a broken contract. See [seed-data.md](./seed-data.md).
- **Schema validation** — the same two commands as `just schema-validate`: the static `@extend_schema` check plus `spectacular --validate --fail-on-warn`.

### Reproducing a failure locally

Every step maps to a `just` recipe:

```bash
just lint             # ruff (CI runs it in --check mode, it won't rewrite)
just test             # pytest
just schema-validate  # both schema steps
just seed && just seed   # idempotency — counts must not move
uv lock --check       # host, no Docker
```

The one thing you can't reproduce with `just` is `makemigrations --check`:

```bash
just manage makemigrations --check --dry-run
```

### Env vars in CI

The `test` job defines its own env block — it does not read `.env`. When you add a **required** env var (one without a default in `environment_variables.py`), add it there too or CI fails at import time with `ImproperlyConfigured`. See [environment.md](./environment.md).

## Dependabot

[`.github/dependabot.yml`](../.github/dependabot.yml) watches three ecosystems:

| Ecosystem | Cadence | Grouping |
|---|---|---|
| `uv` (Python) | weekly, Mondays | one PR for all minor+patch; majors separate; security separate |
| `github-actions` | monthly | one PR for all |
| `docker` (base image) | monthly | one PR |

The grouping is the point. Ungrouped, a weekly Python check opens one PR per package and they get ignored en masse — which is how a repo ends up with 20 open alerts.

Note that Dependabot runs as soon as it sees the config on the default branch — the `interval` governs subsequent runs, not the first one. Expect a burst of PRs the day you merge it, one per accumulated major plus one per group.

### Automated review

The `dependabot` job in `ci.yml` calls the shared [`linkchar-backend-workflows`](https://github.com/Linkcharsoft/linkchar-backend-workflows) review, pinned to a release tag (Dependabot bumps the tag like any other action). After Lint and Tests finish, Claude reads the changelog of every bumped package, checks whether this project uses what changed, and posts a verdict comment. Patch/minor bumps whose verdict is `ok` **and** whose CI passed are squash-merged automatically; a major (or an unknown update type) gets a "Not auto-merged" comment and goes to the panel's runner, which tests it and merges it. Set the `DEPENDABOT_AUTOMERGE` repo variable to `off` to keep the review but never merge.

- **Secret:** `CLAUDE_CODE_OAUTH_TOKEN` must exist both as a *Dependabot* secret and as an *Actions* secret (same value). Without it the review is skipped and nothing merges.
- **Deploying the merge:** a merge made with the workflow's `GITHUB_TOKEN` fires no push workflow, so a project with a deploy workflow sets `deploy-workflow: <its file name>` on the `dependabot` job and grants it `actions: write` (the deploy workflow needs a `workflow_dispatch` trigger that its jobs accept on `main`).
- **Adding a CI job:** add it to the `dependabot` job's `needs` **and** to its `ci-result` expression, or a failure in it will not block the merge.
- Merge policy, inputs and fix commits from trusted actors are documented in the shared repo's README.

### Reviewing a Dependabot PR

What reaches a human is what neither the automated review nor the panel's runner merged: red PRs, and anything the verdict or the runner flagged.

Green checks mean "nothing we test broke." That is most of the answer, and for the grouped minor/patch PR it is normally all of it — merge it.

The gap worth knowing: CI runs the suite, and the suite is small. It cannot see a behavior change in a code path nothing covers. So calibrate by blast radius, not by the green tick alone:

| PR kind | Default action |
|---|---|
| Grouped minor/patch, green | Merge. This is the boring path and it should stay boring. |
| Security advisory, green | Merge, after the exposure check below. |
| **Major**, green | Read the changelog for breaking changes first — that is why majors are ungrouped. |
| Anything touching **auth, storage, or the DB driver** | Read the changelog even for a patch. These fail in ways a small suite misses. |
| Red checks | Never merge to silence it. A red Dependabot PR is CI doing its job — see below. |

**When a Dependabot PR goes red, the bump is usually not the bug.** A tooling upgrade can change what "passing" means: ruff 0.16 began formatting code blocks inside markdown, so the grouped PR carrying it failed `ruff format --check` on files no one had touched. The fix belonged in `pyproject.toml` (exclude `*.md`), on `main`, not in the Dependabot branch — a branch fix gets clobbered on the next rebase, and every future PR would fail the same way.

Ask which of the three it is before touching the branch:

1. **Our code is genuinely incompatible** → fix our code, on its own branch, then rebase the bump onto it.
2. **The tool changed its rules** → adjust the config on `main`, then tell Dependabot to `@dependabot rebase`.
3. **The new version is actually broken** → close the PR and pin the old version with a comment explaining why.

### Triaging an alert

Severity labels rank the *advisory*, not your exposure. Check what the code actually uses before treating a `high` as urgent:

1. **Is the vulnerable API even called?** Grep for it. Most of the PyJWT advisories in the 2026-07 batch were `PyJWKClient`/JWK-specific; this project uses simplejwt with HS256 over `SECRET_KEY` and never constructs a `PyJWKClient`, so real exposure was low.
2. **Is it reachable from untrusted input?** A parser bug in a library that only ever sees your own fixtures ranks below a medium in the auth path.
3. **Is there a patch?** If yes, just take it — arguing about exploitability costs more than the bump.

Then bump the lock only:

```bash
uv lock --upgrade-package <name>
```

`pyproject.toml` constraints are deliberately open, so security patches are usually a lock-only diff. Rebuild (`docker compose build web`) before testing — a new dependency is not in your existing image.

Record the reasoning in the commit body when exposure was low but you bumped anyway. The next person reading `git log` shouldn't have to re-derive it.
