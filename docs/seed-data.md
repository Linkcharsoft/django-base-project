# Seed data

**Scope.** How to fill a dev database with data covering every flow, and what accounts that gives you. Written for whoever is developing the frontend against this backend. Not covered: test fixtures for the pytest suite (see [testing.md](./testing.md)), though both share the same factories.

## Get data

```bash
docker compose up -d
just migrate
just seed
```

That's it. `just seed` is **idempotent** — run it as often as you want, it updates in place instead of duplicating rows.

It refuses to run when `DEBUG=False`, so it can't be pointed at production by accident.

## Accounts

**Every seeded account uses the same password: `Test1234!`**

| Email | State | Use it to test |
|---|---|---|
| `admin@test.com` | staff + superuser, verified, registration complete | Admin-only endpoints (`GET /api/users/`), Django admin at `/admin/` |
| `user@test.com` | regular, verified, registration complete | The happy path. Every authenticated endpoint |
| `incomplete@test.com` | regular, verified, **registration incomplete** | `HasRegisterCompletePermission` → expect `403`. The complete-registration flow |
| `unverified@test.com` | regular, **email not verified** | Login rejection for unverified accounts, resend-verification flow |
| `blocked@test.com` | regular, **`is_active=False`** | Login rejection for blocked accounts, the admin block/unblock toggle |
| `user0@test.com` … `user49@test.com` | regular, verified, complete | Pagination (default page size 10), search, ordering |

Log in at `POST /api/auth/login/` with `{"email": "...", "password": "Test1234!"}` — see [api-contract.md](./api-contract.md).

There is also `admin@admin.com / admin123123`, created by a data migration rather than the seed (see [auth.md](./auth.md#signup)). Prefer `admin@test.com`; that one predates the seed and stays for backwards compatibility.

## Reset

Seeded users all carry `is_test_user=True`, so the existing teardown endpoint wipes them and everything cascading from them:

```bash
curl -X DELETE http://localhost:8001/api/users/delete-test-users/
just seed
```

Nuke everything instead, seeded or not:

```bash
just manage flush --no-input && just seed
```

## What the seed guarantees

Beyond the accounts above, `just seed` covers, for every seeded model: one object per `choices` value, both sides of every boolean, present *and* absent optional relations, and enough rows to exceed one page on any paginated list. If you can reach a screen the seeded data doesn't populate, that's a gap worth reporting — the [coverage rule](../.claude/skills/django-base-seed-data/SKILL.md#coverage-rule--what-all-the-cases-means) says it shouldn't happen.

It also forces `SystemStatus.is_operational = True`. Otherwise every endpoint answers `503` and the backend looks broken (see [auth.md → maintenance flag](./auth.md#global-maintenance-flag)).

## Adding to the seed (backend side)

There is no central seed file. `manage.py seed` calls the `seed()` function of every first-party app that ships a `seeds.py`:

```
<app>/
├── factories.py   # how to build one object   → shared with the test suite
└── seeds.py       # which objects exist in the demo DB
```

Canonical example: [users/factories.py](../users/factories.py) + [users/seeds.py](../users/seeds.py). Full checklist: [`.claude/skills/django-base-seed-data/SKILL.md`](../.claude/skills/django-base-seed-data/SKILL.md).

Seeds run in `INSTALLED_APPS` order. If your app's data depends on another first-party app's rows, declare it after that app in `MY_APPS`. There's no dependency resolver on purpose.

**When you add a model, add it to the seed in the same PR** — and update the table above if you added accounts. A seed that lags behind the models is worse than no seed: the frontend trusts it.
