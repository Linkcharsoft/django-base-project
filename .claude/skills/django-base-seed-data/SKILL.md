---
name: django-base-seed-data
description: Add or extend demo/seed data in the Django base project. Use when you are asked to add seed data, demo data, fixtures, test data, a factory for a model, personas/accounts for frontend testing, or to make `manage.py seed` cover a new model. Also use as the final task of a backlog, to make the seeded scenario coherent across every app that was built.
---

# Django Base — Seed Data

## Overview

`python manage.py seed` (`just seed`) populates a dev database with data the frontend can develop against without touching the backend. It is **idempotent** — re-running updates in place rather than duplicating — and refuses to run unless `DEBUG=True`.

There is no central seed file to edit. The command walks every first-party app, and any app that ships a `seeds.py` with a `seed()` function gets called. Adding a model to the seed means editing (or creating) that one file inside its own app.

## Source Docs

- `docs/seed-data.md` — the persona table the frontend reads. Your changes must keep it accurate.
- `docs/testing.md#factories-not-fixtures-as-json` — the same factories back the test suite.
- `docs/conventions.md#code-organization` — constants, DRY, no speculative abstractions.

## The two files per app

```
<app>/
├── factories.py   # how to build ONE object of each model
└── seeds.py       # WHICH objects the demo database contains
```

Keep the split. A factory that hardcodes a persona is unusable by tests; a `seeds.py` that inlines field values duplicates the factory.

### `factories.py`

One `DjangoModelFactory` per model. Canonical example: [users/factories.py](../../../users/factories.py).

- **`django_get_or_create` on a natural key is mandatory** — that is what makes re-running the seed idempotent. Without it the second `just seed` duplicates every row.
- `factory.Faker(...)` for filler values, `factory.Sequence(...)` for anything that must be unique.
- `factory.SubFactory(OtherFactory)` for FKs — never create the parent by hand inside the child factory.
- Expose non-field setup (related rows, post-save state) as `@factory.post_generation` hooks with a keyword name, so `seeds.py` reads as flags: `UserFactory(verified=False)`.
- Set the project's test marker when the model has one — `is_test_user=True` on users — so the existing `DELETE /api/users/delete-test-users/` teardown reaches the data.

### `seeds.py`

Must define `seed()`. Return a one-line summary string (the command prints it), or `None`.

```python
from <app>.factories import ThingFactory

BULK = 50

PERSONAS = [
    {"name": "...", "state": "..."},
]


def seed():
    for persona in PERSONAS:
        ThingFactory(**persona)
    ThingFactory.create_batch(BULK)
    return f"{len(PERSONAS) + BULK} things"
```

## Workflow

1. **Read `docs/seed-data.md`** to see what already exists. Do not re-seed something another app already covers.
2. **Inspect the target model**: every field with choices, every boolean, every nullable FK, every state-machine-ish field.
3. **Write/extend `factories.py`** for the model.
4. **Write/extend `seeds.py`** with one object per *meaningful state*, plus a bulk batch when the resource is listed by a paginated endpoint.
5. **Update `docs/seed-data.md`** — the table row for the new data, and the credentials if you added accounts. The frontend reads only that file.
6. **Verify**: `just seed` twice in a row. Second run must not change the row counts. Then `just lint` and `just test`.

## Coverage rule — what "all the cases" means

For every model you seed, cover:

| Field kind | Seed at least |
|---|---|
| `choices` | one object per choice |
| `BooleanField` | one `True`, one `False` |
| nullable FK / `blank=True` | one with the relation, one without |
| status / state field | one object per state the frontend renders differently |
| any paginated list endpoint | enough rows to exceed one page (default page size is 10) |
| `FileField` / `ImageField` | one with a file, one without — the frontend has to render both |

If the frontend can render a screen you cannot reach with the seeded data, the seed is incomplete.

## Do not

- Do not write JSON fixtures (`loaddata`/`dumpdata`). They rot when the schema changes; see `docs/testing.md`.
- Do not add a `--fresh` / wipe flag. Reset already exists: `DELETE /api/users/delete-test-users/` cascades the test data, then re-seed.
- Do not create a central `seeds.py` that imports from other apps — each app seeds itself, ordering comes from `INSTALLED_APPS`.
- Do not randomize the identity of a persona. Emails, slugs, and any value the frontend hardcodes must be literals, not `Faker`.
- Do not seed anything behind a real external service. Mock it and add the `SETUP_REQUIRED.md` entry instead.

## Ordering

Seeds run in `INSTALLED_APPS` order, which means `MY_APPS` declaration order. If your app's data needs another first-party app's rows to exist, declare your app **after** it in `django_base/settings/custom_settings.py`. There is no dependency resolver — this is the whole mechanism.
