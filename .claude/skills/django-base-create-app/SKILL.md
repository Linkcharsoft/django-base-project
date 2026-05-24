---
name: django-base-create-app
description: Create or register first-party Django apps inside the Django base project. Use when you are asked to add a new app, run startapp, add a domain module, register an app in settings, or create the app-level urls.py router shell while following this template's conventions. If the request includes CRUD, API resources, serializers, viewsets, endpoints, or router registration for an actual resource, use django-base-add-api-resource as the next step.
---

# Django Base — Create App

## Overview

Use this skill to add first-party domain apps to the Django base template without drifting into generic Django patterns. Keep the repo docs as the source of truth and use this skill as the execution checklist.

## Related Skills

- Use `django-base-add-env-var` when the new app introduces a feature flag, secret, or any per-environment setting.
- Use `django-base-add-api-resource` when the app needs a CRUD/API resource, serializers, viewsets, router entries, permissions, schema annotations, or API tests.

## Source Docs

Start with the repo's docs, then inspect existing app code before editing:

- Grep `docs/_agent-index.md` for `add app`, `startapp`, `apps`, or the user's domain word.
- Read `docs/development-guide.md#recipe-add-an-app`.
- Read `docs/architecture.md#apps-inventory` when adding an app that should be documented.
- Check `docs/README.md#updating-these-docs` when behavior changes.

## Workflow

1. Discover local patterns:
   - Inspect `users/` and any similar first-party app before creating files.
   - Inspect `django_base/settings/custom_settings.py` for the current first-party app list.
   - Inspect `django_base/urls.py` for router mounting style.

2. Create the app:
   - Use `just manage startapp <name>`.
   - Confirm the app folder is at the repo root, matching existing first-party apps.
   - Register first-party apps in the existing local app list, currently `MY_APPS` in `django_base/settings/custom_settings.py`.

3. App URL shell:
   - If the app will expose API resources now or soon, create `<app>/urls.py` with a DRF `DefaultRouter` exposed as a module-level `router` (the name is load-bearing because `django_base/urls.py` imports app routers by that name).
   - Keep this file minimal when there is no resource yet:

     ```python
     # <app>/urls.py
     from rest_framework.routers import DefaultRouter

     router = DefaultRouter()
     ```

   - Mount the app router in `django_base/urls.py` only when it has registered routes, unless the project already keeps empty app routers mounted.
   - Do not add a separate `path("api/...", include(...))` entry for the app; API resources should flow through `base_router`.

4. Documentation:
   - If the app changes project structure or behavior, update the relevant docs in the same change.
   - Update `docs/architecture.md` when the app should appear in folder layout or apps inventory.
   - Add or adjust `docs/_agent-index.md` rows when a new concept should be discoverable by agents.

5. Verification:
   - Run focused tests while developing when possible.
   - Run `just lint` and `just test` before declaring work done.
   - Run `just schema-validate` only if this app creation also adds API-visible routes.

## Useful Skeletons

Use the existing codebase first; these are only memory aids.

```python
# <app>/urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
```
