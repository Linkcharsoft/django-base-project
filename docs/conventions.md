# Conventions

Patterns, helpers, and tools used in this codebase. New code should follow these unless there's a specific reason not to.

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

Default page size is **10** with `max_page_size=100`. Configured by `CustomPagination` in `django_base/base_utils/base_pagination.py`. Clients can pass `?page=...&page_size=...`.

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

`django_base/base_utils/utils.unicode_random_string` is **not** what you want for security. The project uses `get_random_string` from the same module for password recovery tokens. If you need cryptographically random strings, prefer `secrets.token_urlsafe(...)` from the stdlib.

## Email helpers

In `django_base/base_utils/utils.py`:

- `get_default_for_email_template()` → dict with `APP_NAME`, banner URL, etc. Spread into your template context.
- `email_template_sender(subject, template_path, context, to_email)` → renders the template (using the Django template engine with the project `templates/` dir) and sends via the configured `EMAIL_BACKEND`.

Templates live in `templates/registration/` and `templates/account/` (allauth defaults). Override the allauth ones by copying the same file path with your changes.

## i18n

- `LANGUAGES = [("en", "English")]` in `configurations.py`.
- Source strings use `gettext` / `gettext_lazy` (aliased `_`).
- `.po` files in `locale/<lang>/LC_MESSAGES/`.
- `just messages` extracts new strings; `just compilemessages` builds `.mo`.

## Toolchain

The project ships with a fixed, opinionated toolchain — described below.

### justfile

Task runner — replaces the ad-hoc shell scripts and the old `runcommands.py`. Install on Windows with `winget install Casey.Just`, macOS `brew install just`, elsewhere `cargo install just`.

```bash
just              # lists every recipe
just up           # docker compose up -d
just test         # pytest
just manage <x>   # python manage.py <x>
```

Special directives at the top of `justfile`:

- `set dotenv-load := true` — auto-loads `.env` so recipes can reference `$DB_USER` etc.
- `set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]` — required on Windows because `just` defaults to `sh`, which isn't on Windows PATH.

### uv

Used inside the Dockerfile for dependency installation:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY requirements.txt ./
RUN uv pip sync --system requirements.txt
```

To regenerate `requirements.txt` locally (or inside the container):

```bash
uv pip compile pyproject.toml -o requirements.txt
```

### ruff

Lint + format. Configured in `pyproject.toml`. Run via:

- `just lint` — formats and auto-fixes.
- Pre-commit hook (`ruff` + `ruff-format`) runs automatically on `git commit`.
- Manually inside container: `docker compose exec web ruff check .`.

A blame-skip commit hash for the initial mass-format pass is recorded in `.git-blame-ignore-revs`.

### pre-commit

Hooks defined in `.pre-commit-config.yaml`. Install once after cloning:

```bash
pre-commit install
```

Active hooks:

- `pre-commit-hooks v5.0.0` — trailing whitespace, end-of-file, YAML/TOML checks, merge conflict markers, large file guard, debug-statement guard.
- `ruff-pre-commit v0.8.0` — `ruff` + `ruff-format`.
- `django-upgrade 1.30.0` — auto-upgrades Django patterns to `--target-version 5.2`.

Bump versions with `pre-commit autoupdate` (review the diff before committing; new ruff versions can introduce new lint rules).

### Spectacular schema

OpenAPI 3.1 schema is generated at runtime. Validate it before releases:

```bash
just schema-validate          # fails on warnings
```

Annotate non-trivial actions with `@extend_schema(request=..., responses=...)` to keep the schema accurate. Every viewset MUST set `serializer_class` or override `get_serializer_class`; otherwise spectacular ignores it.

## Testing

- `pytest` + `pytest-django` (configured in `pyproject.toml`).
- Tests live next to the app: `<app>/tests.py`.
- Run with `just test`; HTML coverage with `just coverage`.
- **Status (as of 2026-05-14)**: test files are scaffolded but mostly empty. Backlog item 6.4 covers writing the real suite.
