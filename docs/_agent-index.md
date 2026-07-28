# Agent index

**Purpose.** Keyword → file:anchor lookup table, optimized for AI agents (and humans in a hurry). Grep this file with the keyword closest to your question; the right row tells you where to read next.

The leading `_` keeps it at the top of `ls` / file pickers. This is the **only** file in `docs/` whose primary audience is an agent.

## How to use

1. Pick the closest keyword from the left column (synonyms are listed — match any of them).
2. Open the linked file at the listed anchor.
3. If the linked file doesn't fully answer, follow its own cross-references.

If your question isn't here, add a row in your PR.

## Index

### Setup, env, tools

| Keywords | Where |
|---|---|
| install, clone, first time, setup, prerequisites | [quickstart.md](./quickstart.md) |
| env var, environment variable, `.env`, secret, configuration | [environment.md](./environment.md) |
| add new env var, register env var | [environment.md → checklist](./environment.md#adding-a-new-env-var-checklist) |
| feature flag, `USE_DEBUG_TOOLBAR`, `USE_S3` | [environment.md → compile-time flags](./environment.md#compile-time-flags-not-env-vars) |
| celery, background jobs, redis, broker | [extending/celery.md](./extending/celery.md) |
| websocket, channels, asgi, daphne, realtime | [extending/websockets.md](./extending/websockets.md) |
| country, state, city, places, location, region | [extending/global-places.md](./extending/global-places.md) |
| google oauth, social login, socialaccount, SocialApp, CLIENT_ID, CLIENT_SECRET | [extending/google-oauth.md](./extending/google-oauth.md) |
| just, justfile, task runner, recipe, command | [toolchain.md → justfile](./toolchain.md#justfile) |
| uv, pip, requirements, dependencies | [toolchain.md → uv](./toolchain.md#uv) |
| ruff, lint, format, style | [toolchain.md → ruff](./toolchain.md#ruff) |
| pre-commit, hook | [toolchain.md → pre-commit](./toolchain.md#pre-commit) |
| openapi, schema, swagger, spectacular | [toolchain.md → drf-spectacular](./toolchain.md#drf-spectacular) |
| extend_schema, @action schema, response envelope, custom action openapi | [conventions.md → openapi schema](./conventions.md#openapi-schema) |
| schema filter, hide endpoint, preprocessing hook, exclude path from openapi, dj-rest-auth filter | [django_base/openapi.py](../django_base/openapi.py) + [api-contract.md → /api/auth/](./api-contract.md#apiauth) |

### Architecture / where things are

| Keywords | Where |
|---|---|
| folder layout, project structure, what lives where | [architecture.md → folder layout](./architecture.md#folder-layout) |
| settings, split-settings, configuration file order | [architecture.md → settings split](./architecture.md#settings-split) |
| middleware, middleware order, request order | [architecture.md → middleware stack](./architecture.md#middleware-stack) |
| url, route, urlconf, mounted apps | [architecture.md → URL layout](./architecture.md#url-layout) |
| apps, installed apps, inventory | [architecture.md → apps inventory](./architecture.md#apps-inventory) |
| optional feature, s3, sentry, debug toolbar | [architecture.md → optional features](./architecture.md#optional-features-off-by-default) |
| critical, do not break, fragile | [architecture.md → critical files](./architecture.md#critical-files-do-not-break) |
| request flow, lifecycle, middleware chain, how a request gets handled | [request-lifecycle.md](./request-lifecycle.md) |
| where to hook in, custom middleware, custom auth | [request-lifecycle.md → where to hook in](./request-lifecycle.md#where-to-hook-in) |

### API contract

| Keywords | Where |
|---|---|
| endpoint, route inventory, what endpoints exist | [api-contract.md](./api-contract.md) |
| user endpoint, `/api/users/`, user crud | [api-contract.md → /api/users/](./api-contract.md#apiusers) |
| auth endpoint, login, logout, register | [api-contract.md → /api/auth/](./api-contract.md#apiauth) |
| system status, maintenance, is-system-up | [api-contract.md → /api/system-status/](./api-contract.md#apisystem-status) |
| healthcheck, load balancer probe | [api-contract.md → /healthcheck/](./api-contract.md#healthcheck) |
| throttle, rate limit | [api-contract.md → throttling](./api-contract.md#throttling) |
| breaking change, deprecate, contract | [api-contract.md → breaking change rules](./api-contract.md#breaking-change-rules) |
| put 405, no put, why patch | [api-contract.md](./api-contract.md) + [conventions.md → viewset mixins](./conventions.md#viewset-mixins) |

### Auth

| Keywords | Where |
|---|---|
| login, jwt, access token, refresh token | [auth.md → login](./auth.md#login-email--password) |
| jwt lifetime, jwt expiration, jwt rotation | [auth.md → stack](./auth.md#stack) |
| signup, registration, register | [auth.md → signup](./auth.md#signup) |
| password recovery, forgot password, reset password | [auth.md → password recovery](./auth.md#password-recovery) |
| password change, change password | [auth.md → password change](./auth.md#password-change-authenticated) |
| `PASSWORD_CHANGE_BY_EMAIL`, gate password change | [auth.md → password change](./auth.md#password-change-authenticated) |
| google oauth, social login, socialapp | [extending/google-oauth.md](./extending/google-oauth.md) |
| permission, `IsAdminUser`, `HasRegisterCompletePermission` | [auth.md → permissions](./auth.md#permissions) |
| maintenance flag, kill switch, `SystemStatus`, 503 | [auth.md → maintenance flag](./auth.md#global-maintenance-flag) |
| test user, `is_test_user`, e2e teardown, delete test users | [api-contract.md → /api/users/](./api-contract.md#apiusers) |

### Code patterns

| Keywords | Where |
|---|---|
| code organization, design, clean code, SOLID, OOP, refactor | [conventions.md → code organization](./conventions.md#code-organization) |
| import at top, circular import, deferred import, `PLC0415`, `TYPE_CHECKING` | [conventions.md → imports go at the top](./conventions.md#imports-go-at-the-top-of-the-file) |
| constant, magic number, hardcoded string, literal, where to define | [conventions.md → constants have exactly one home](./conventions.md#constants-have-exactly-one-home) |
| duplicated logic, DRY, copy paste, repeated code, extract helper | [conventions.md → don't abstract on the first write](./conventions.md#dont-abstract-on-the-first-write-do-extract-on-the-second) |
| class vs functions, inheritance, composition, mixin, abstraction, service class | [conventions.md → class or module of functions](./conventions.md#class-or-module-of-functions) |
| BaseModel, `created_at`, `updated_at`, abstract base | [conventions.md → BaseModel](./conventions.md#basemodel) |
| BaseSerializer | [conventions.md → BaseSerializer](./conventions.md#baseserializer) |
| viewset, mixin, `BaseModelViewSet`, `NoPutViewSetMixin` | [conventions.md → viewset mixins](./conventions.md#viewset-mixins) |
| permission per action, `permissions = {...}` dict | [conventions.md → ViewSetPermissionMixin](./conventions.md#viewsetpermissionmixin) |
| serializer per action, `serializers = {...}` dict | [conventions.md → ViewSetSerializerMixin](./conventions.md#viewsetserializermixin) |
| pagination, page size, `CustomPagination` | [conventions.md → pagination](./conventions.md#pagination) |
| file upload, `ImageField`, `FileField`, `unique_upload_to`, avatar | [conventions.md → file uploads](./conventions.md#file-uploads) |
| password validator, `UpperValidator`, `SymbolValidator` | [conventions.md → custom password validators](./conventions.md#custom-password-validators) |
| email helper, send email from view, template sender | [conventions.md → email helpers](./conventions.md#email-helpers) |
| i18n, translation, gettext, `.po`, `.mo` | [conventions.md → i18n](./conventions.md#i18n) |

### Recipes (how do I add X)

| Keywords | Where |
|---|---|
| add model | [development-guide.md → add a model](./development-guide.md#recipe-add-a-model) |
| add endpoint, add crud, new viewset, new resource | [development-guide.md → add a CRUD endpoint](./development-guide.md#recipe-add-a-crud-endpoint) |
| add action, custom action, `@action`, archive endpoint | [development-guide.md → add a custom action](./development-guide.md#recipe-add-a-custom-action) |
| add app, `startapp`, new django app | [development-guide.md → add an app](./development-guide.md#recipe-add-an-app) |
| add permission class, custom permission | [development-guide.md → add a permission class](./development-guide.md#recipe-add-a-permission-class) |
| add env var | [environment.md → checklist](./environment.md#adding-a-new-env-var-checklist) |
| send email, transactional email, email from view | [development-guide.md → send an email from a view](./development-guide.md#recipe-send-an-email-from-a-view) |
| feature flag, gate feature | [development-guide.md → gate a feature behind a flag](./development-guide.md#recipe-gate-a-feature-behind-a-flag) |
| migration, deploy migration, zero-downtime migration | [development-guide.md → migration safely](./development-guide.md#recipe-add-a-migration-safely-production) |
| translation string, gettext, translate | [development-guide.md → add a translation string](./development-guide.md#recipe-add-a-translation-string) |
| throttle scope, custom rate limit | [development-guide.md → add a throttled scope](./development-guide.md#recipe-add-a-throttled-scope) |

### Testing

| Keywords | Where |
|---|---|
| run tests, pytest | [testing.md → running](./testing.md#running) |
| test layout, where tests live | [testing.md → layout](./testing.md#layout) |
| test convention, factory boy, fixtures | [testing.md → conventions](./testing.md#conventions) |
| seed, demo data, test data, populate db, `just seed`, frontend testing | [seed-data.md](./seed-data.md) |
| test accounts, demo credentials, personas, test password | [seed-data.md → accounts](./seed-data.md#accounts) |
| factory, `factories.py`, `seeds.py`, add model to seed | [seed-data.md → adding to the seed](./seed-data.md#adding-to-the-seed-backend-side) + [skill](../.claude/skills/django-base-seed-data/SKILL.md) |
| reset data, wipe test users, flush db | [seed-data.md → reset](./seed-data.md#reset) |
| test maintenance mode, 503 in tests | [testing.md → maintenance mode in tests](./testing.md#maintenance-mode-in-tests) |
| test throttle, 429 in tests | [testing.md → throttling in tests](./testing.md#throttling-in-tests) |

### Deployment / ops

| Keywords | Where |
|---|---|
| production deploy, gunicorn, prod compose | [deployment.md → production image](./deployment.md#production-image) |
| static files, whitenoise, collectstatic | [deployment.md → static and media](./deployment.md#static-and-media) |
| s3 media, public media storage | [deployment.md → static and media](./deployment.md#static-and-media) |
| nginx, reverse proxy | [deployment.md → reverse proxy](./deployment.md#reverse-proxy-nginx) |
| aws logs, cloudwatch | [deployment.md → AWS CloudWatch logs](./deployment.md#aws-cloudwatch-logs) |
| email provider, ses, smtp, transactional email | [deployment.md → email](./deployment.md#email) |
| healthcheck, load balancer probe | [deployment.md → healthcheck](./deployment.md#healthcheck) |
| maintenance mode, toggle maintenance | [deployment.md → maintenance mode](./deployment.md#maintenance-mode) |
| sentry, error tracking, monitoring | [deployment.md → environment](./deployment.md#environment) |
| migration deploy, production migration order | [deployment.md → migration deploy flow](./deployment.md#migration-deploy-flow) |

### Task workflow (autonomous subagents)

| Keywords | Where |
|---|---|
| task workflow, autonomous loop, subagent loop, planner, runner, reviewer | [task-workflow.md](./task-workflow.md) |
| tasks.md, backlog, T001, pending, status pending | [task-workflow.md → state files](./task-workflow.md#state-files) |
| django-task-planner, plan tasks, requirements to tasks | [.claude/agents/django-task-planner.md](../.claude/agents/django-task-planner.md) |
| django-task-runner, implement task, autonomous builder | [.claude/agents/django-task-runner.md](../.claude/agents/django-task-runner.md) |
| django-task-reviewer, review diff, convention check | [.claude/agents/django-task-reviewer.md](../.claude/agents/django-task-reviewer.md) |
| just task-run, run-tasks.sh, task loop, claude-tasks branch | [task-workflow.md → running it](./task-workflow.md#running-it) |
| quota, session limit, 5-hour limit, usage limit, overnight run, max-quota-wait, weekly cap | [task-workflow.md → quota handling](./task-workflow.md#quota-handling) |
| just review, review.log | [task-workflow.md → running it](./task-workflow.md#running-it) |
| just task-log, pretty-print log, stream-json log | [task-workflow.md → state files](./task-workflow.md#state-files) |
| progress/, T00N-done.md, progress note | [task-workflow.md → state files](./task-workflow.md#state-files) |
| SETUP_REQUIRED.md, human-blocked, mock, manual config | [task-workflow.md → state files](./task-workflow.md#state-files) |
| loop stalled, agent not advancing, MaxStalled | [task-workflow.md → when the loop stops](./task-workflow.md#when-the-loop-stops) |

### Troubleshooting

| Keywords | Where |
|---|---|
| just not found, command not found | [troubleshooting.md → `just: command not found`](./troubleshooting.md#just-command-not-found) |
| docker compose v1, `docker-compose` not found | [troubleshooting.md → docker compose](./troubleshooting.md#docker-compose-command-not-found-or-docker-compose-is-invoked) |
| postgres connection refused, db unreachable | [troubleshooting.md → connection refused](./troubleshooting.md#psycopgoperationalerror-connection-refused) |
| port 8000 in use | [troubleshooting.md → port 8000](./troubleshooting.md#port-8000-already-in-use) |
| ImproperlyConfigured | [troubleshooting.md → ImproperlyConfigured](./troubleshooting.md#improperlyconfigured-set-the-x-environment-variable) |
| relation does not exist, migrate | [troubleshooting.md → relation does not exist](./troubleshooting.md#djangodbutilsprogrammingerror-relation--does-not-exist) |
| no changes detected (migrations) | [troubleshooting.md → no changes detected](./troubleshooting.md#no-changes-detected-but-you-edited-a-model) |
| inconsistent migration history | [troubleshooting.md → InconsistentMigrationHistory](./troubleshooting.md#inconsistentmigrationhistory) |
| email not verified, login 400 | [troubleshooting.md → email not verified](./troubleshooting.md#login-returns-400-e-mail-address-is-not-verified) |
| social app not found, google oauth setup | [extending/google-oauth.md](./extending/google-oauth.md) |
| 503 every endpoint | [troubleshooting.md → every endpoint 503](./troubleshooting.md#every-endpoint-suddenly-returns-503) |
| schema validate fails | [troubleshooting.md → schema-validate fails](./troubleshooting.md#just-schema-validate-fails) |
| 405 on PUT | [troubleshooting.md → PUT 405](./troubleshooting.md#put-apiusers1-returns-405) |
| sentry not capturing | [troubleshooting.md → sentry not capturing](./troubleshooting.md#sentry-not-capturing-errors) |
| static files 404 prod | [troubleshooting.md → static 404](./troubleshooting.md#static-files-404-in-production) |

## Maintenance

If you add a doc, add its keywords here. If you rename an anchor, grep this file for the old anchor name. Prefer adding a row to renaming an existing one — synonyms are cheap.
