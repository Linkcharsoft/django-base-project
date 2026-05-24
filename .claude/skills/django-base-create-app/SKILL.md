---
name: django-base-create-app
description: Create or extend first-party Django apps inside the Django base project. Use when you are asked to add a new app, run startapp, add a domain module, add a CRUD endpoint/resource, create models/serializers/viewsets/routers for a new app, or wire a new app into django_base/urls.py and settings while following this template's conventions.
---

# Django Base — Create App

## Overview

Use this skill to add first-party domain apps to the Django base template without drifting into generic Django patterns. Keep the repo docs as the source of truth and use this skill as the execution checklist.

## Related Skills

- Use `django-base-add-env-var` when the new app introduces a feature flag, secret, or any per-environment setting.

## Source Docs

Start with the repo's docs, then inspect existing app code before editing:

- Grep `docs/_agent-index.md` for `add app`, `startapp`, `crud`, `viewset`, `BaseModel`, or the user's domain word.
- Read `docs/development-guide.md#recipe-add-an-app` and, when endpoints are involved, `docs/development-guide.md#recipe-add-a-crud-endpoint`.
- Read `docs/conventions.md` for `BaseModel`, `BaseSerializer`, viewset mixins, per-action permissions/serializers, and `unique_upload_to`.
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

3. Model conventions:
   - Use `BaseModel` for models that need `created_at` and `updated_at`; do not add those fields manually.
   - Use `unique_upload_to(subdir)` for every `FileField` or `ImageField`.
   - Add app-local validators, permissions, or services only when the behavior belongs to the app.
   - Run `just makemigrations` after model changes and review generated migrations.

4. API conventions:
   - Use `BaseSerializer` for project-conventional serializers.
   - Use `BaseModelViewSet` for mutable CRUD resources and `BaseReadOnlyModelViewSet` for read-only resources.
   - Always set `serializer_class` on viewsets so drf-spectacular can see the endpoint.
   - Use `permissions = {"action": [...], "default": [...]}` instead of overriding `get_permissions` for simple action dispatch.
   - Use `serializers = {"action": Serializer, "default": Serializer}` instead of overriding `get_serializer_class` for simple action dispatch.
   - Use `[AllowAny]` explicitly for public endpoints; never use an empty permission list.
   - Do not implement PUT flows. `NoPutViewSetMixin` blocks PUT; use PATCH for updates and custom actions.

5. Router conventions:
   - Create `<app>/urls.py` with a DRF `DefaultRouter` exposed as a module-level `router` (the name is load-bearing — `django_base/urls.py` imports it by that name).
   - In `django_base/urls.py`, import the router with an alias matching existing apps and extend `base_router.registry`. Pattern:

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

   - Do not add a separate `path("api/...", include(...))` entry for the app; the `base_router` mount under `/api/` already covers it.

6. Documentation:
   - If behavior, API shape, env vars, conventions, or setup steps change, update the relevant doc in the same change.
   - Add or adjust `docs/_agent-index.md` rows when a new concept should be discoverable by agents.

7. Verification:
   - Run focused tests while developing when possible.
   - Run `just schema-validate` when serializers, viewsets, routers, permissions, or OpenAPI-visible behavior changed.
   - Run `just lint` and `just test` before declaring work done.

## Useful Skeletons

Use the existing codebase first; these are only memory aids.

```python
from django_base.base_utils.base_models import BaseModel


class Widget(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
```

```python
from django_base.base_utils.base_serializers import BaseSerializer


class WidgetSerializer(BaseSerializer):
    class Meta:
        model = Widget
        fields = ("id", "name")
```

```python
from rest_framework.permissions import IsAuthenticated

from django_base.base_utils.base_viewsets import BaseModelViewSet


class WidgetViewSet(BaseModelViewSet):
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer
    permissions = {
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "default": [IsAuthenticated],
    }
    serializers = {
        "default": WidgetSerializer,
    }
```
