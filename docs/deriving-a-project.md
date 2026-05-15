# Deriving a project from this base

**Scope.** Kickoff steps when starting a new Linkchar project from `django-base-project`. What to rename, what to keep, what to delete. Not covered: ongoing development (see [development-guide.md](./development-guide.md)).

This base is the starting point for ~every Django project at Linkchar. Treat it like a snapshot: fork once, then diverge.

## 1. Clone, don't fork

You generally want a fresh repo, not a GitHub fork (which entangles upstream history). Two options:

**Option A — fresh history** (recommended for client projects):

```bash
git clone <base-repo-url> my-project
cd my-project
rm -rf .git
git init
git add -A
git commit -m "Initial commit (django-base-project @ <base-sha>)"
git remote add origin <new-repo-url>
git push -u origin main
```

Note the base commit SHA in the initial commit message — it's the only paper trail of where the project started.

**Option B — preserve history** (when you want to cherry-pick upstream improvements later):

```bash
git clone <base-repo-url> my-project
cd my-project
git remote rename origin base
git remote add origin <new-repo-url>
git push -u origin main
# Later, to pull a base improvement:
git fetch base && git cherry-pick <sha-from-base>
```

## 2. Rename the project

These references to `django_base` / `APP_NAME` need updating. Do them in this order:

| Place | What to change |
|---|---|
| [`django_base/`](../django_base/) folder | Rename to `<project_slug>/` (keep snake_case). |
| `manage.py` | `DJANGO_SETTINGS_MODULE = "<project_slug>.settings"` |
| `Dockerfile` | Any reference to `django_base.wsgi` → `<project_slug>.wsgi`. |
| `docker-compose.yml` + `docker-compose-production.yml` | `command:` line gunicorn `django_base.wsgi:application` → `<project_slug>.wsgi:application`. |
| `entrypoint.sh` / `entrypoint-dev.sh` | Any `django_base` references. |
| `pyproject.toml` | `[tool.pytest.ini_options] DJANGO_SETTINGS_MODULE` |
| `django_base/asgi.py` `wsgi.py` `urls.py` | Internal imports use the new package name. |
| `django_base/settings/configurations.py` | `APP_NAME = "<Human Readable>"` (used in email subjects + OpenAPI title). |
| `django_base/settings/custom_settings.py` | `SPECTACULAR_SETTINGS["TITLE"]` if you want a custom API title. |
| `readme.md` (root) | Project name + short description. |
| `.env.example` | Adjust `DEFAULT_FROM_EMAIL`, `FRONT_URL` defaults. |

Quick sweep:

```bash
grep -r "django_base" --exclude-dir=.git --exclude-dir=data .
```

…then update each hit.

## 3. Decide which optional features you need

Edit [`django_base/settings/configurations.py`](../django_base/settings/configurations.py):

| Flag | Turn ON when… |
|---|---|
| `USE_DEBUG_TOOLBAR` | Dev convenience. Leave OFF in any deployed environment. |

Env-driven flags:

- `USE_S3=True` — only when you have an S3 bucket and AWS credentials.
- `IS_PRODUCTION=True` — only on actual production environments. Activates Sentry init.

If the project needs background jobs or realtime, follow [`extending/celery.md`](./extending/celery.md) or [`extending/websockets.md`](./extending/websockets.md) — they're not shipped by default.

## 4. Decide auth posture

- **Default**: `PASSWORD_CHANGE_BY_EMAIL=True`. Users always go through the recovery flow to change passwords. Most secure, slightly more friction.
- **Alternative**: set `PASSWORD_CHANGE_BY_EMAIL=False` if the product needs an in-app password change form. See [auth.md → password change](./auth.md#password-change-authenticated).

If the project needs Google OAuth, follow [extending/google-oauth.md](./extending/google-oauth.md). It's not shipped by default.

## 5. Wipe what you don't need

| Path | Delete when… |
|---|---|
| `users/migrations/0002_*` and onward | Keep `0001_initial` only if you'll modify the User model significantly. Otherwise keep all. |
| `templates/registration/password_recovery_email.html` | Replace with your branding. |
| `templates/account/email/*` (allauth) | Replace with your branding. |
| `locale/<langs you don't ship>/` | If you only ship English, delete the others. |

## 6. First custom changes

1. Add your first domain app: `just manage startapp <domain>`. See [development-guide.md → add an app](./development-guide.md#recipe-add-an-app).
2. Wire its router into [`django_base/urls.py`](../django_base/urls.py).
3. Write a smoke test that hits `/api/<domain>/` and asserts 200/403.
4. Update [`docs/api-contract.md`](./api-contract.md) with the new endpoints.
5. Update [`docs/architecture.md → Apps inventory`](./architecture.md#apps-inventory).

## 7. Set up CI/CD (not provided by the base)

The base ships with `.github.base/` (intentionally not active) as scaffolding. Move/rename to `.github/` and adapt the workflows when you have a target host. At minimum:

- Run `just lint` + `just test` on PR.
- Run `just schema-validate` on PR.
- Build + push the Docker image on `main` merges.

## 8. Document what's different

Keep `docs/` and update each file as you diverge:

- **`docs/architecture.md`** — apps inventory, anything you've added.
- **`docs/api-contract.md`** — new endpoints.
- **`docs/environment.md`** — new env vars.
- **`docs/deployment.md`** — your actual hosting setup (nginx config, ECS/Fly/Render specifics).

Keep `docs/conventions.md`, `docs/toolchain.md`, `docs/development-guide.md`, `docs/request-lifecycle.md` mostly as-is — they describe the *base* and rarely diverge.

## Checklist (copy into your kickoff PR)

```markdown
- [ ] Renamed django_base/ → <project_slug>/
- [ ] Swept the codebase for `django_base` references
- [ ] Updated APP_NAME, DEFAULT_FROM_EMAIL, FRONT_URL defaults
- [ ] Picked feature flags (USE_DEBUG_TOOLBAR; added Celery/Channels if needed via docs/extending/)
- [ ] Decided PASSWORD_CHANGE_BY_EMAIL posture
- [ ] Replaced email templates with brand assets
- [ ] Configured CI (lint + test + schema-validate)
- [ ] Updated docs/architecture.md and docs/api-contract.md
- [ ] Recorded base commit SHA in initial commit message
```
