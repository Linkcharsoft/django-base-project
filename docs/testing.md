# Testing

**Scope.** How tests are organized, how to run them, and what conventions new tests should follow. Not covered: what CI runs on every PR — see [ci.md](./ci.md).

## Status

As of **2026-05-14**, test files are scaffolded (`<app>/tests.py` exists in every app) but mostly empty. Backlog item 6.4 covers writing a real suite. Treat this doc as the target conventions for that work.

## Stack

- **`pytest`** + **`pytest-django`** — configured in [`pyproject.toml`](../pyproject.toml) `[tool.pytest.ini_options]`.
- **`coverage`** — HTML report via `just coverage`.
- Tests run inside the `web` container against a **real Postgres** (`db` service from compose). No SQLite fallback — production parity matters.

## Layout

```
<app>/
├── models.py
├── views.py
└── tests.py          # or tests/ package with multiple modules once it grows
```

When `tests.py` outgrows one file, convert to a package:

```
<app>/tests/
├── __init__.py
├── conftest.py       # app-local fixtures
├── test_views.py
├── test_models.py
└── test_permissions.py
```

Shared fixtures (cross-app) go in a top-level `conftest.py` at the repo root.

## Running

```bash
just test                                          # full suite
docker compose exec web pytest users/                                # one app
docker compose exec web pytest users/tests.py::TestUserViewSet::test_list_admin_only  # one test
just coverage                                      # full suite + HTML report under htmlcov/
```

The `test` recipe in `justfile` does not currently forward arguments. To run a subset, call `pytest` inside the container directly (or extend the recipe with `args` variadic params).

`pytest-django` reuses the DB across runs (`--reuse-db` is the default in `pyproject.toml`). Pass `--create-db` when you've added migrations and the schema is stale.

## Conventions

### Use the API client, not the unit-level view

Most of the surface area we want to protect is at the HTTP boundary (permissions, serializers, routing). Prefer:

```python
from rest_framework.test import APIClient

from users.factories import UserFactory

def test_users_list_is_admin_only(db):
    client = APIClient()
    client.force_authenticate(user=UserFactory(is_staff=False))
    response = client.get("/api/users/")
    assert response.status_code == 403
```

Over direct viewset method calls.

### Factories, not fixtures-as-JSON

Use `factory_boy` over JSON fixtures. JSON fixtures rot when the schema changes; factories adapt.

Factories live in `<app>/factories.py` and are **shared with the demo seed** — [users/factories.py](../users/factories.py) is the canonical one. Write the factory once and both the test suite and `just seed` get it. See [seed-data.md](./seed-data.md) for the seed side.

### One assertion per behavior

A test that asserts "list returns 403 for non-admin" should not also assert pagination metadata. Split.

### Test what's risky, not what's covered by the framework

Don't write tests that re-verify Django/DRF behavior. Test:

- Permission classes (especially `HasRegisterCompletePermission` and per-action `permissions = {...}`)
- Custom validators (`UpperValidator`, `SymbolValidator`, `FileSizeValidator`)
- Signals (`Profile.create_profile` on `User.post_save`)
- Custom serializers (`CustomRegisterSerializer`, `UserListSerializer` slim payload)
- Middleware (`IsSystemUpMiddleware` exempt-path logic)
- Password recovery flow end-to-end (token → check → confirm)
- The `delete_test_users` open endpoint contract

### Maintenance mode in tests

`IsSystemUpMiddleware` reads `SystemStatus.is_operational` from the DB. Tests that hit any endpoint **other than** the exempt paths will 503 if a prior test set `is_operational=False` and didn't reset. Use a fixture to reset:

```python
@pytest.fixture(autouse=True)
def _system_is_up(db):
    from platform_configurations.models import SystemStatus
    SystemStatus.objects.update_or_create(pk=1, defaults={"is_operational": True})
```

### Throttling in tests

`password_recovery` is throttled to `5/hour`. To avoid flakiness in tests that loop the flow:

```python
from rest_framework.test import override_settings

@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon": "1000/min", "user": "1000/min", "password_recovery": "1000/hour"}})
def test_recovery_flow(...): ...
```

## Coverage targets (proposed)

When the suite is written, the baseline floor should be:

| Path | Target |
|---|---|
| `users/permissions.py`, `*/middlewares.py` | 100% |
| Custom serializers, validators | ≥95% |
| Viewset action methods | ≥80% |
| Admin / migrations | not tracked |
