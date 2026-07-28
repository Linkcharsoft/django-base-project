---
name: django-base-add-api-resource
description: Add or modify API resources in the Django base project. Use when you are asked to add a CRUD endpoint, API resource, serializer, viewset, router registration, custom DRF action, per-action permissions or serializers, OpenAPI-visible behavior, or tests for an endpoint in an existing or newly created app. Use alongside django-base-create-app when the app itself does not exist yet.
---

# Django Base — Add API Resource

## Overview

Use this skill to add or change DRF API resources without drifting into generic Django/DRF patterns. This applies whether the app already exists or was just created.

## Related Skills

- Use `django-base-create-app` first when the app package itself does not exist.
- Use `django-base-add-env-var` when the resource introduces a per-environment setting, secret, or feature flag.

## Source Docs

Start with the repo's docs, then inspect existing code:

- Grep `docs/_agent-index.md` for `add endpoint`, `crud`, `viewset`, `serializer`, `permissions`, `router`, or the user's domain word.
- Read `docs/development-guide.md#recipe-add-a-crud-endpoint`.
- Read `docs/development-guide.md#recipe-add-a-custom-action` when adding a custom action.
- Read `docs/conventions.md` for `BaseModel`, `BaseSerializer`, viewset mixins, per-action permissions/serializers, and file uploads.
- Read `docs/api-contract.md` before changing public API shape.
- Check `docs/README.md#updating-these-docs` when behavior changes.

## Workflow

1. Discover local patterns:
   - Inspect the target app's `models.py`, `serializers.py`, `views.py`, `urls.py`, tests, and any filters/permissions.
   - Inspect `users/` or another similar first-party app when the target app has no pattern yet.
   - Inspect `django_base/urls.py` for router mounting style.

2. Model conventions:
   - Use `BaseModel` for models that need `created_at` and `updated_at`; do not add those fields manually.
   - Use `unique_upload_to(subdir)` for every `FileField` or `ImageField`.
   - Add app-local validators, permissions, services, or filters only when the behavior belongs to the app.
   - Run `just makemigrations` after model changes and review generated migrations.

3. Serializer conventions:
   - Use `BaseSerializer` for project-conventional serializers.
   - Create separate list/detail/write serializers only when the API shape needs them.
   - Keep `fields` explicit unless the surrounding app uses a different established pattern.

4. Viewset conventions:
   - Use `BaseModelViewSet` for mutable CRUD resources.
   - Use `BaseReadOnlyModelViewSet` for list/retrieve-only resources.
   - Use `queryset = Model.objects.all()` unless the app has a scoped manager/query pattern.
   - Declare the serializer via `serializers = {"default": Serializer}` (and per-action keys when needed). Do not also set `serializer_class` — the dict's `"default"` is what drf-spectacular reads.
   - Use `permissions = {"action": [...], "default": [...]}` instead of overriding `get_permissions` for simple action dispatch.
   - Use `[AllowAny]` explicitly for public endpoints; never use an empty permission list.
   - Do not implement PUT flows. `NoPutViewSetMixin` blocks PUT; use PATCH for updates and custom actions.

5. Custom actions:
   - Use `@action` from DRF. Prefer `methods=["patch"]` for state changes.
   - Add matching `permissions` and `serializers` entries for the action.
   - **Every `@action` must be decorated with `@extend_schema(request=..., responses=...)`**, no exceptions. drf-spectacular can't infer the response envelope for actions that return anything other than the default serializer (custom dicts like `{"detail": "..."}` or `{"items": [...], "total": N}`), so without `@extend_schema` the generated OpenAPI lies. This is enforced by `scripts/check_api_schema.py` which runs as part of `just schema-validate`. Canonical example: `users/views.py` (`complete_register`, `toggle_block`, `delete_test_users`).
   - For syntax, use `docs/development-guide.md#recipe-add-a-custom-action`; for the project-canonical shape, copy `users/views.py`.

6. Router conventions:
   - Ensure `<app>/urls.py` exposes a module-level DRF `DefaultRouter` named `router`.
   - Register the resource on that router.
   - In `django_base/urls.py`, import the app router with a clear alias and extend `base_router.registry`.
   - Do not add a separate `path("api/...", include(...))` entry for the app; the `base_router` mount under `/api/` already covers it.

   ```python
   # <app>/urls.py
   from rest_framework.routers import DefaultRouter

   from .views import WidgetViewSet

   router = DefaultRouter()
   router.register(r"widgets", WidgetViewSet)
   ```

   ```python
   # django_base/urls.py
   from widgets.urls import router as widgets_router
   # ...
   base_router.registry.extend(widgets_router.registry)
   ```

7. Seed data (do this in the same task, not later):
   - Add a `DjangoModelFactory` for the new model in `<app>/factories.py`, with `django_get_or_create` on a natural key so the seed stays idempotent. The test suite uses this same factory.
   - Extend (or create) `<app>/seeds.py` so `just seed` produces data the frontend can actually render: one object per `choices` value, both sides of every boolean, present and absent optional relations, and enough rows to pass the first page of any paginated list.
   - Update `docs/seed-data.md` only if you added accounts or changed credentials.
   - Full checklist and the coverage rule: `.claude/skills/django-base-seed-data/SKILL.md`.

8. Documentation:
   - Update `docs/api-contract.md` for new, removed, or changed endpoints/methods/payloads.
   - Update `docs/architecture.md` if the app inventory or URL layout changes.
   - Update `docs/_agent-index.md` when a new endpoint/resource/concept should be discoverable.
   - If the resource needs an env var, switch to `django-base-add-env-var` for that change — do not edit `docs/environment.md` directly from here.

9. Verification:
   - Add or update focused API tests for the resource, permissions, and important failure cases.
   - Run focused tests while developing when possible.
   - Run `just schema-validate` after serializers, viewsets, routers, permissions, or OpenAPI-visible behavior changed.
   - Run `just lint` and `just test` before declaring work done.
