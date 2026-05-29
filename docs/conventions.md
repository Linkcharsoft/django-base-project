# Conventions

**Scope.** Code-level patterns and helpers used across the project. New code should follow these unless there's a specific reason not to. Not covered: build/dev tools (see [toolchain.md](./toolchain.md)), testing (see [testing.md](./testing.md)).

## BaseModel

Defined in `django_base/base_utils/base_models.py`. Every model that needs `created_at`/`updated_at` should inherit from it:

```python
from django_base.base_utils.base_models import BaseModel

class MyModel(BaseModel):
    name = models.CharField(max_length=100)
```

Adds two fields:

- `created_at = DateTimeField(auto_now_add=True)`
- `updated_at = DateTimeField(auto_now=True)`

It is `abstract = True`, so no extra table is created.

## BaseSerializer

Defined in `django_base/base_utils/base_serializers.py`. Inherit when you want a serializer to follow the project conventions (currently a thin wrapper; centralized so future conventions can be added in one place).

## Viewset mixins

The project provides a stack of mixins in `django_base/base_utils/base_viewsets.py` that compose three concerns:

- **`NoPutViewSetMixin`** — blocks `PUT`, returns `405`. Forces clients to use `PATCH`.
- **`ViewSetPermissionMixin`** — per-action permission dispatch (see below).
- **`ViewSetSerializerMixin`** — per-action serializer dispatch.

Use the pre-composed classes:

| Class | Stack |
|---|---|
| `BaseGenericViewSet` | NoPut + Permission + Serializer + `GenericViewSet` |
| `BaseReadOnlyModelViewSet` | Permission + Serializer + `ReadOnlyModelViewSet` |
| `BaseModelViewSet` | NoPut + Permission + Serializer + `ModelViewSet` |

### `ViewSetPermissionMixin`

Instead of overriding `get_permissions`, declare a dict:

```python
class MyViewSet(BaseModelViewSet):
    permissions = {
        "list": [IsAdminUser],
        "retrieve": [IsAuthenticated],
        "create": [IsAuthenticated],
        "default": [HasRegisterCompletePermission],
    }
    extra_permissions = []   # appended to whichever action runs
```

Empty list = misconfiguration → raises an `AssertionError` at request time. Use `[AllowAny]` explicitly for public endpoints.

### `ViewSetSerializerMixin`

Same pattern for serializers:

```python
class MyViewSet(BaseModelViewSet):
    serializers = {
        "list": MyListSerializer,
        "retrieve": MyDetailSerializer,
        "default": MyDetailSerializer,
    }
```

`None` value or missing default → `AssertionError`. Override `get_serializer_class` only if the dispatch needs more than action-name matching.

## Pagination

`CustomPagination` (`django_base/base_utils/base_pagination.py`) is a thin `PageNumberPagination` subclass that adds `page_size_query_param="page_size"` and `max_page_size=100`. The **default page size of 10** comes from `REST_FRAMEWORK["PAGE_SIZE"]` in `django_base/settings/custom_settings.py`, not the class. Clients can pass `?page=...&page_size=...` (capped at 100).

## File uploads

Use `unique_upload_to(subdir)` from `django_base/base_utils/base_uploads.py` for any `FileField` or `ImageField`. It renames the file to `<subdir>/<uuid4>.<ext>` so two uploads with the same name don't collide.

Combine with the size validator and Django's extension validator:

```python
from django.core.validators import FileExtensionValidator
from django.db import models

from django_base.base_utils.base_uploads import unique_upload_to
from django_base.base_utils.base_validators import FileSizeValidator

class Profile(BaseModel):
    avatar = models.ImageField(
        upload_to=unique_upload_to("avatars"),
        validators=[
            FileSizeValidator(mb_limit=5),
            FileExtensionValidator(["jpg", "jpeg", "png"]),
        ],
        blank=True,
    )
```

## Custom password validators

In `django_base/base_utils/base_validators.py`:

- `UpperValidator` — at least one uppercase letter.
- `SymbolValidator` — at least one ASCII punctuation char.
- `NumberRequiredValidator` — at least one digit (not currently wired into `AUTH_PASSWORD_VALIDATORS`; add it if you need it).

Plus `FileSizeValidator` (above).

## Random tokens / strings

`django_base/base_utils/utils.py:get_random_string(length)` is what the project uses for password recovery tokens. It's built on `random.choices` over `string.ascii_letters + string.digits` — fine for that use, but **not cryptographically secure**. If you need security-grade randomness (CSRF nonces, session-like tokens), prefer `secrets.token_urlsafe(...)` from the stdlib.

## Email helpers

In `django_base/base_utils/utils.py`:

- `get_default_for_email_template()` → dict with `APP_NAME`, banner URL, etc. Spread into your template context.
- `email_template_sender(subject, template_name, context, to_email, from_email=DEFAULT_FROM_EMAIL, attachments=None)` → renders `template_name` via the Django template engine (project `templates/` dir is on the loader path) and sends via the configured `EMAIL_BACKEND`. Note: `email_template_sender` *also* calls `get_default_for_email_template()` internally, so you don't need to merge it into context manually — but it doesn't hurt.

Templates live in `templates/registration/` and `templates/account/` (allauth defaults). Override the allauth ones by copying the same file path with your changes.

## OpenAPI schema

`drf-spectacular` introspects every viewset and generates the OpenAPI 3.1 schema served at `/api/schema/`. The frontend and the Postman/Swagger consumers depend on this schema being accurate.

- **Every `@action` must declare `@extend_schema(request=..., responses=...)`** — both for built-in actions (`@action(detail=False, methods=["get"])`) and detail actions. Spectacular cannot infer the response envelope when the action returns anything other than the viewset's default serializer (e.g. `{"detail": "..."}`, a custom paginated envelope, a `{"items": [...], "total": N}` shape). Without `@extend_schema`, spectacular emits a *silently wrong* schema that compiles fine but lies about the real response.
- This is enforced by `python scripts/check_api_schema.py`, which is wired ahead of `manage.py spectacular --validate --fail-on-warn` inside `just schema-validate`. The check fails the build when an `@action` is missing the decorator.
- For viewsets, set the per-action serializer via `serializers = {"action_name": Serializer}` — that's also what spectacular reads for `list`/`retrieve`/`create`/`update`/`partial_update`/`destroy`. Do **not** also set `serializer_class`.
- Canonical example: [users/views.py](../users/views.py) `complete_register`, `toggle_block`, `delete_test_users`. Copy that shape.

## i18n

- `LANGUAGES = [("en", "English")]` in `configurations.py`.
- Source strings use `gettext` / `gettext_lazy` (aliased `_`).
- `.po` files in `locale/<lang>/LC_MESSAGES/`.
- `just messages` extracts new strings; `just compilemessages` builds `.mo`.

## Where this leaves off

- **Tools** (just, uv, ruff, pre-commit, drf-spectacular) → [toolchain.md](./toolchain.md).
- **Testing** (pytest setup, fixtures, conventions) → [testing.md](./testing.md).
- **Adding a new endpoint / app / model** → [development-guide.md](./development-guide.md).
