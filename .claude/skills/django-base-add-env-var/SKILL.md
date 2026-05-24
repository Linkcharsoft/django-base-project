---
name: django-base-add-env-var
description: Add, rename, remove, or change defaults for environment variables in the Django base project. Use when you are asked to add an env var, feature flag, secret, setting driven by deployment configuration, .env.example entry, django-environ parsing, or any settings value that differs per environment.
---

# Django Base — Add Env Var

## Overview

Use this skill to keep env var parsing centralized and documented in the Django base template. The rule is simple: parse env vars once in `django_base/settings/environment_variables.py`, then import parsed values elsewhere.

## Filter First — Is This Actually An Env Var?

Before doing anything else, answer: **does this value change per deployment environment, or is it a secret?**

- **Yes** → continue with this skill.
- **No** (project-shape constant, tunable that derived projects may change once at fork time, business rule that does not vary between dev/staging/prod) → put it in `django_base/settings/configurations.py` instead and stop. Do not add it as an env var.

This is the most common mistake: not every tunable belongs in `.env`. Env vars carry deployment ceremony (`.env.example` row, docs row, agent-index row, Docker/CI wiring). Use them only when you need that ceremony.

## Source Docs

Once the filter says "yes, this is an env var", start with the repo's docs and current settings before editing:

- Grep `docs/_agent-index.md` for `env var`, the env var name, the feature name, or `settings`.
- Read `docs/environment.md#adding-a-new-env-var-checklist`.
- Read `docs/README.md#updating-these-docs` because env var changes require doc updates.
- Inspect `django_base/settings/environment_variables.py`, the consuming settings file, and `.env.example`.

## Related Skills

- Use `django-base-create-app` when the env var is being introduced as part of a new first-party app (e.g. a feature flag that gates the app's wiring).

## Workflow

1. Choose the contract:
   - Pick an uppercase snake-case env var name.
   - Decide type and default. Follow the repo checklist's preference for a sensible default unless the value is deliberately required for boot, such as `SECRET_KEY`.
   - Optional features must default off or to a harmless value so the base boots without optional services.
   - Prefer explicit `env.bool`, `env.str`, `env.int`, `env.list`, or another `django-environ` helper matching nearby code.

2. Parse once:
   - Add the parsed value in `django_base/settings/environment_variables.py`.
   - Do not call `os.environ`, `environ.Env()`, or `env(...)` from another settings file.
   - Keep naming consistent: env var `MY_VAR` becomes exported setting constant `MY_VAR`.

3. Consume by import:
   - In the consuming settings module, import from `django_base.settings.environment_variables`.
   - Keep optional integrations gated with top-level settings-time `if` blocks when they alter `INSTALLED_APPS`, middleware, caches, channels, Celery, S3, Sentry, or similar wiring.
   - Do not inline optional feature setup into the base when an extending guide should own it.

4. Update env templates and docs:
   - Add the variable to `.env.example` with a placeholder and short comment.
   - Update `docs/environment.md`, keeping the variable in the correct table and following the existing grouping/order.
   - Check and update `docs/_agent-index.md` for every env var add, rename, removal, or default change.
   - Update feature docs under `docs/extending/` when the env var belongs to an optional integration.

5. Verify:
   - Run `just lint`.
   - Run `just test`.
   - Run a settings/import check when useful, for example `just manage check`.

## Patterns

Optional flag:

```python
# django_base/settings/environment_variables.py
USE_EXAMPLE_FEATURE = env.bool("USE_EXAMPLE_FEATURE", default=False)
```

Deliberately required value:

```python
# django_base/settings/environment_variables.py
EXAMPLE_API_KEY = env.str("EXAMPLE_API_KEY")
```

Use this no-default pattern only when the project should fail to boot without the value.

Consuming settings:

```python
from django_base.settings.environment_variables import USE_EXAMPLE_FEATURE


if USE_EXAMPLE_FEATURE:
    INSTALLED_APPS += ["example_feature"]
```

Never add:

```python
import os

VALUE = os.environ.get("MY_VAR")
```
