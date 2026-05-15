# Extending: Celery (background jobs)

**Scope.** How to add Celery + Redis to the project for asynchronous task execution.
**Not covered.** Channels / WebSockets (see [websockets.md](./websockets.md)) — they happen to also use Redis but the config is independent.

The base intentionally ships **without** Celery: the old `django_base/celery.py` + `USE_CELERY` flag + `BROKER_*` envs were removed because they couldn't actually run (the `celery` lib was not declared). Follow this guide to wire it back in two minutes when the project actually needs it.

---

## When you need it

- Sending emails outside the request/response cycle.
- Long-running jobs (report generation, third-party API sync, image processing).
- Scheduled tasks (replacement for cron — pair with `django-celery-beat`).

If you only need *fire-and-forget* without retries or scheduling, consider `asyncio.create_task` or a thread pool first. Celery is heavyweight.

## Infrastructure prerequisite

A Redis (or RabbitMQ) broker reachable from the web container. In Linkchar, the `base-infra` stack already provides one — point `BROKER_URL` at it.

Locally, add a Redis service to `docker-compose.yml`:

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

And add `redis` to the `depends_on` list of the `web` service.

---

## Step-by-step

### 1. Add the dependencies

```bash
uv add celery redis
just build
```

`uv add` updates `pyproject.toml` (`[project.dependencies]`) and `uv.lock` in one step. Commit both.

### 2. Create `django_base/celery.py`

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_base.settings")

app = Celery("django_base")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### 3. Register the app in `django_base/__init__.py`

```python
from django_base.celery import app as celery_app

__all__ = ("celery_app",)
```

This ensures Celery loads when Django starts so `@shared_task` decorators work everywhere.

### 4. Add env vars

In `.env.example`:

```bash
# <-------------- Celery -------------->
CELERY_BROKER_URL='redis://redis:6379/0'
CELERY_RESULT_BACKEND='redis://redis:6379/0'
```

In `django_base/settings/environment_variables.py`:

```python
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/0")
```

In `django_base/settings/custom_settings.py` (after the existing imports, anywhere near the bottom):

```python
from django_base.settings.environment_variables import CELERY_BROKER_URL, CELERY_RESULT_BACKEND  # add to existing import block

# Celery
CELERY_TASK_ALWAYS_EAGER = False  # set True in test settings to run tasks synchronously
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
```

The `namespace="CELERY"` in step 2 means every `CELERY_*` setting in Django is forwarded to Celery automatically.

### 5. Add a worker service to `docker-compose.yml`

```yaml
  worker:
    build: .
    command: celery -A django_base worker -l info
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - .:/code
```

For production (`docker-compose-production.yml`), drop the bind mount and use the same image as `web`:

```yaml
  worker:
    build: .
    command: celery -A django_base worker -l info --concurrency=4
    env_file:
      - .env
    restart: unless-stopped
```

### 6. Optional — scheduled tasks (`django-celery-beat`)

```bash
uv add django-celery-beat
```

Then in `custom_settings.py`:

```python
INSTALLED_APPS += ["django_celery_beat"]
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
```

Run `just migrate` and add a `beat` service to compose:

```yaml
  beat:
    build: .
    command: celery -A django_base beat -l info -S django_celery_beat.schedulers:DatabaseScheduler
    env_file:
      - .env
    depends_on:
      - db
      - redis
```

### 7. Write a task

In any app, create `tasks.py`:

```python
from celery import shared_task


@shared_task
def send_welcome_email(user_id: int) -> None:
    from users.models import User

    user = User.objects.get(pk=user_id)
    # send mail …
```

Call it from a view:

```python
from .tasks import send_welcome_email

send_welcome_email.delay(user.id)
```

### 8. Justfile shortcut (optional)

```just
# Tail celery worker logs
worker-logs:
    docker compose logs -f worker

# Open a celery shell (introspect tasks)
worker-shell:
    docker compose exec worker celery -A django_base inspect active
```

---

## Validation

1. `just build && just up` — `worker` service comes up healthy in `docker compose logs worker`.
2. From the Django shell: `from users.tasks import some_task; some_task.delay()` — should return an `AsyncResult` with an ID and the worker logs should show the task executing.
3. If `result.get(timeout=5)` hangs → check broker connectivity (`docker compose exec web python -c "import redis; redis.Redis(host='redis').ping()"`).

## Testing

For tests, force eager execution so tasks run synchronously:

```python
# tests fixture or test settings
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

## Production notes

- **Don't share the broker** between Celery and Channels — separate Redis databases (`/0` vs `/1`) at minimum, ideally separate instances.
- **Result backend is optional** — if you don't call `.get()` on task results, drop `CELERY_RESULT_BACKEND` and save the Redis writes.
- **Monitor worker queue depth** (Flower, Sentry's Celery integration, or Prometheus exporter). A growing queue means workers are under-provisioned.
- **Graceful shutdown** — workers must finish in-flight tasks on SIGTERM. Compose's default 10s grace period is usually too short for jobs; set `stop_grace_period: 60s` on the `worker` service.
