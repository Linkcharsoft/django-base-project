# Development guide

**Scope.** Step-by-step recipes for common changes: adding endpoints, apps, models, env vars, migrations. Each recipe lists *exactly* the files to touch. Not covered: the *why* behind these patterns (see [conventions.md](./conventions.md)) or the tools they use (see [toolchain.md](./toolchain.md)).

## Recipe: add a model

1. Pick the right app (or create one — see "add an app").
2. In `<app>/models.py`:

   ```python
   from django.db import models
   from django_base.base_utils.base_models import BaseModel

   class Widget(BaseModel):                         # ← inherit BaseModel for created_at/updated_at
       name = models.CharField(max_length=100)
       owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="widgets")

       class Meta:
           ordering = ["-created_at"]

       def __str__(self):
           return self.name
   ```

3. `just makemigrations` → `just migrate`.
4. Register in `<app>/admin.py` if it needs admin visibility.

**Don't** add a `created_at`/`updated_at` manually — `BaseModel` already does it.

## Recipe: add a CRUD endpoint

Assume you have a `Widget` model and want `/api/widgets/`.

1. **Serializer** — `<app>/serializers.py`:

   ```python
   from django_base.base_utils.base_serializers import BaseSerializer
   from .models import Widget

   class WidgetSerializer(BaseSerializer):
       class Meta:
           model = Widget
           fields = ("id", "name", "owner", "created_at")
           read_only_fields = ("id", "created_at")

   class WidgetListSerializer(BaseSerializer):     # slim payload for `list`
       class Meta:
           model = Widget
           fields = ("id", "name")
   ```

2. **Viewset** — `<app>/views.py`:

   ```python
   from rest_framework.permissions import IsAuthenticated, IsAdminUser
   from django_base.base_utils.base_viewsets import BaseModelViewSet
   from users.permissions import HasRegisterCompletePermission
   from .models import Widget
   from .serializers import WidgetSerializer, WidgetListSerializer

   class WidgetViewSet(BaseModelViewSet):
       queryset = Widget.objects.all()
       serializer_class = WidgetSerializer          # required for drf-spectacular

       permissions = {
           "list":    [IsAuthenticated],
           "retrieve": [IsAuthenticated],
           "create":  [HasRegisterCompletePermission],
           "default": [IsAdminUser],
       }
       serializers = {
           "list":    WidgetListSerializer,
           "default": WidgetSerializer,
       }
   ```

3. **Router** — `<app>/urls.py`:

   ```python
   from rest_framework.routers import DefaultRouter
   from .views import WidgetViewSet

   router = DefaultRouter()
   router.register(r"widgets", WidgetViewSet, basename="widget")
   ```

4. **Mount** — append to `base_router` in [`django_base/urls.py`](../django_base/urls.py):

   ```python
   from widgets.urls import router as widgets_router
   base_router.registry.extend(widgets_router.registry)
   ```

5. **Verify**: `just schema-validate` and check `/api/schema/swagger-ui/`.

**Note.** `PUT` is disabled automatically because `BaseModelViewSet` includes `NoPutViewSetMixin`. Use `PATCH`.

## Recipe: add a custom action

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class WidgetViewSet(BaseModelViewSet):
    ...
    @action(detail=True, methods=["patch"], url_path="archive")
    def archive(self, request, pk=None):
        widget = self.get_object()
        widget.archived = True
        widget.save(update_fields=["archived", "updated_at"])
        return Response({"status": "archived"})
```

Then permission/serializer dispatch keys match the action name:

```python
permissions = {"archive": [IsAdminUser], "default": [...]}
serializers = {"archive": ArchiveSerializer, "default": WidgetSerializer}
```

Annotate with `@extend_schema(request=ArchiveSerializer, responses=...)` so the schema stays accurate.

## Recipe: add an app

1. `just manage startapp <name>`.
2. Move the new folder to the repo root (it'll be created under `django_base/` by Django; not what we want).
3. Register in `BASE_APPS` (`django_base/settings/django_settings.py`) or `INSTALLED_APPS` extension in `custom_settings.py`. Keep first-party apps in `BASE_APPS`.
4. Create `<app>/urls.py` with a `DefaultRouter` named `router` (the project convention — `base_router.registry.extend(...)` expects it).
5. Mount in `django_base/urls.py` (see the CRUD recipe step 4).

## Recipe: add a permission class

`users/permissions.py` is the canonical home for project-wide permission classes. App-local permissions go in `<app>/permissions.py`.

```python
from rest_framework.permissions import BasePermission

class IsWidgetOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
```

Reference it from the viewset's `permissions` dict.

## Recipe: add an env var

See [environment.md → Adding a new env var](./environment.md#adding-a-new-env-var-checklist).

## Recipe: add a settings constant

Project-shape constants (not env-driven) live in [`django_base/settings/configurations.py`](../django_base/settings/configurations.py). Add one when:

- The value should change across derived projects without env-var ceremony.
- It's referenced from multiple settings files.

If the value is env-driven, prefer adding it to `.env.example` + `environment_variables.py` instead.

## Recipe: send an email from a view

```python
from django_base.base_utils.utils import email_template_sender, get_default_for_email_template

context = get_default_for_email_template()
context.update({"user_name": user.first_name})
email_template_sender(
    subject="Welcome",
    template_name="registration/welcome.html",
    context=context,
    to_email=user.email,
)
```

Template files live in `templates/registration/` (or `templates/account/` for allauth overrides). See [auth.md → password recovery](./auth.md#password-recovery) for the canonical example.

## Recipe: gate a feature behind a flag

1. Decide: env var (per-environment) or `configurations.py` constant (per-project)?
2. Use a top-level `if` in the settings file, not at request time:

   ```python
   # custom_settings.py
   if USE_DEBUG_TOOLBAR:
       INSTALLED_APPS += ["debug_toolbar"]
       MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
   ```

   Request-time `if settings.USE_X` is fine for view logic but **not** for `INSTALLED_APPS` or middleware registration.

## Recipe: add a migration safely (production)

1. Make the migration backwards-compatible with the *previous* code version (no `RemoveField` in the same release as the code change that stops using the field).
2. `just makemigrations`. Review the generated file — split it if it does too much.
3. Test locally: `just migrate --plan` then `just migrate`.
4. Commit the migration file alongside the model change.
5. Deploy order in prod: run migration → deploy code → run cleanup migration in next release.

See [deployment.md → migration deploy flow](./deployment.md#migration-deploy-flow).

## Recipe: add a translation string

1. Wrap in `gettext_lazy` (aliased `_`):

   ```python
   from django.utils.translation import gettext_lazy as _
   raise serializers.ValidationError(_("Widget name is required"))
   ```

2. `just messages` → edit `locale/<lang>/LC_MESSAGES/django.po`.
3. `just compilemessages` to build `.mo`.

## Recipe: add a throttled scope

```python
# custom_settings.py — DEFAULT_THROTTLE_RATES
"widget_create": "10/minute",
```

```python
# views.py
class WidgetViewSet(BaseModelViewSet):
    throttle_scope = "widget_create"   # applied to all actions; for per-action, override get_throttles()
```

## Files you should know exist

| Want to change… | File |
|---|---|
| The middleware list | [`django_base/settings/django_settings.py`](../django_base/settings/django_settings.py) |
| DRF settings (auth, throttling, pagination) | [`django_base/settings/custom_settings.py`](../django_base/settings/custom_settings.py) |
| URL roots | [`django_base/urls.py`](../django_base/urls.py) |
| BaseModel / BaseSerializer / mixins | [`django_base/base_utils/`](../django_base/base_utils/) |
| User / Profile / TokenRecovery models | [`users/models.py`](../users/models.py) |
| Custom register serializer | [`users/serializers.py`](../users/serializers.py) |
| Allauth adapter | [`users/adapter.py`](../users/adapter.py) |
| Password recovery views | [`auth_api/views.py`](../auth_api/views.py) |
| Maintenance middleware | [`platform_configurations/middlewares.py`](../platform_configurations/middlewares.py) |
| Email templates | [`templates/registration/`](../templates/registration/), [`templates/account/`](../templates/account/) |
