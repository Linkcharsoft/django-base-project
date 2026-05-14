# Fase 6 — Backlog menor

**Esfuerzo:** variable (cada item es independiente) · **Riesgo:** Bajo · **Breaking para el front:** Caso por caso

---

## 📌 Contexto

Esta fase agrupa mejoras menores que no encajan en ninguna de las fases 1-5 pero que vale la pena hacer. Son **independientes entre sí**: cada item puede abordarse en su propia sesión limpia sin ejecutar los otros.

Antes de empezar leé [README.md](./README.md) para contexto general.

---

## 🎯 Objetivo

Dejar limpio el resto del proyecto después de las fases mayores.

---

## 📋 Items del backlog

Cada item incluye problema, ubicación, fix sugerido y esfuerzo.

### Item 6.1 — Refactor `runcommands.py` → Makefile o justfile

**Problema:** `runcommands.py` (~8 KB) es un script Python custom que envuelve comandos Docker (migrations, tests, shell, etc.). Reinventa la rueda — `make` o [`just`](https://github.com/casey/just) son estándares, más mantenibles y no requieren Python local.

**Ubicación:** `runcommands.py` (raíz)

**Plan sugerido:**

1. Leer `runcommands.py` y listar los comandos que expone (con sus descripciones).
2. Crear un `Makefile` (o `justfile`) en la raíz con equivalentes. Ejemplo:

```makefile
.PHONY: build up down logs shell migrate makemigrations test coverage messages compilemessages

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell_plus

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

test:
	docker compose exec web pytest

coverage:
	docker compose exec web pytest --cov --cov-report=html

messages:
	docker compose exec web python manage.py makemessages -a

compilemessages:
	docker compose exec web python manage.py compilemessages
```

3. Eliminar `runcommands.py`.
4. Actualizar `readme.md` con las nuevas invocaciones (`make shell` en vez del menú interactivo de runcommands).

**Esfuerzo:** 1 h · **Breaking:** No (es tooling local)

---

### Item 6.2 — Renombrar app `auth/` → `auth_api`

**Problema:** tener una app custom llamada `auth` colisiona conceptualmente con `django.contrib.auth`. No da error porque el import es `from auth.views import ...` (path-based), pero es confuso y arriesgado: cualquier import mal escrito puede tocar una cosa en vez de la otra.

**Ubicación:** directorio `auth/` y todos sus imports.

**Plan sugerido:**

1. Renombrar directorio: `git mv auth auth_api`.
2. Actualizar `apps.py` dentro del módulo: `name = "auth_api"`.
3. Actualizar `INSTALLED_APPS` en `custom_settings.py` — ojo, actualmente la app `auth` **no está en `INSTALLED_APPS`**, solo se importa en `urls.py`. Confirmarlo con grep antes de asumir nada.
4. Actualizar el include en `django_base/urls.py`:
   ```python
   path("api/auth/", include("auth_api.urls")),
   ```
   ⚠ **No cambiar el path URL** — sigue siendo `api/auth/`. Solo cambia el nombre del módulo Python.
5. Buscar y reemplazar imports:
   ```bash
   grep -rn "from auth\." --include="*.py" .
   grep -rn "^import auth" --include="*.py" .
   ```
6. Verificar que `migrate` no se queja (si hubiera migraciones, hay que manejar `app_label`; actualmente `auth/migrations/` está vacío excepto `__init__.py`, así que no debería haber problema).

**Esfuerzo:** 1 h · **Breaking:** No para el front (la URL `/api/auth/...` no cambia). Sí puede romper ramas de desarrollo — avisar al equipo backend.

---

### Item 6.3 — Endurecer `platform_configurations.middlewares.IsSystemUpMiddleware`

**Problema:** el middleware depende de que la tabla `platform_configurations_systemstatus` exista. En el primer `migrate` o en un CI con DB fresca, carga antes de que la tabla esté creada y puede romper el startup.

Además la lógica de exclusión (`admin`, superuser, path `system-status/is-system-up/`) está hardcoded con matching frágil por `url_name`.

**Ubicación:** `platform_configurations/middlewares.py`

**Plan sugerido:**

1. Leer el archivo completo.
2. Envolver el acceso a `SystemStatus.objects.get_or_create(pk=1)` en `try/except OperationalError`, y devolver "sistema OK" si la tabla aún no existe.
3. En lugar de chequear `resolver_match.url_name == "..."` hardcoded, usar una tupla de paths exentos definida en settings:
   ```python
   SYSTEM_STATUS_EXEMPT_PATHS = ("admin/", "api/system-status/", "/static/", "/media/")
   ```
4. Arreglar el typo del viewset: `SytemStatusViewSet` → `SystemStatusViewSet` (afecta `platform_configurations/views.py`, `platform_configurations/urls.py` y cualquier referencia).

**Esfuerzo:** 1-2 h · **Breaking:** No (URL `system-status/is-system-up/` se mantiene).

---

### Item 6.4 — Escribir tests reales (auth y users)

**Problema:** `auth/tests.py`, `users/tests.py` y `platform_configurations/tests.py` están **vacíos** (solo el comentario "# Create your tests here"). Cero cobertura, cero tests de regresión para bugs como los fixeados en Fase 1.

**Ubicación:** los 3 archivos `tests.py`.

**Plan sugerido:**

Crear un set mínimo que cubra:

1. **`auth/tests.py`**:
   - Password recovery end-to-end: POST a `/password/recovery/` → extraer token de la BD → POST a `/password/recovery/check-token/` → POST a `/password/recovery/confirm/` → login con la nueva password.
   - Rate limiting: 6 POST a `/password/recovery/` desde la misma IP deben devolver 429 en el 6°.
   - Login con credenciales correctas devuelve JWT.
   - Login con credenciales inválidas devuelve 401.
   - Google OAuth view responde 400 sin token (no espera que funcione el flow completo sin mocks).

2. **`users/tests.py`**:
   - `GET /api/users/` como admin devuelve 200.
   - `GET /api/users/` como usuario normal devuelve 403.
   - `PATCH /api/users/me/` como user autenticado modifica el propio usuario.
   - `PATCH /api/users/complete-register/` marca `profile.is_register_complete=True`.
   - `PATCH /api/users/{id}/toggle-block/` con bool `False` bloquea (test de regresión para el bug de Fase 1.4).
   - `DELETE /api/users/delete-test-users/` sin auth devuelve 401 o 404 según opción elegida en Fase 1.3.

3. **`platform_configurations/tests.py`**:
   - `GET /api/system-status/is-system-up/` devuelve 200 con el estado del sistema.
   - Middleware: con `SystemStatus.is_operational=False`, cualquier request fuera del endpoint exento devuelve 503.

Usar `pytest-django` (ya está en requirements) y el `APIClient` de DRF. Considerar instalar `factory-boy` + `faker` de nuevo (se sacaron en Fase 2) **si y solo si** se van a escribir muchos tests.

**Esfuerzo:** 4-8 h (cobertura mínima) · **Breaking:** No

---

### Item 6.5 — Squash migraciones de `users/`

**Problema:** `users/migrations/` tiene 3 archivos (`0001_initial.py`, `0002_auto_20230504_1107.py`, `0003_user_is_test_user.py`). En un template base, es razonable mantener una sola migración `0001_initial` para que nuevos proyectos arranquen limpios.

**Ubicación:** `users/migrations/`

**Plan sugerido:**

1. `docker compose exec web python manage.py squashmigrations users 0001 0003`
2. Revisar el archivo squasheado generado (`0001_squashed_XXX.py`).
3. Eliminar las 3 migraciones originales (tras confirmar que el squash las replica correctamente).
4. Renombrar el squash a `0001_initial.py`.
5. Probar en una DB nueva: `docker compose down -v && docker compose up -d && docker compose exec web python manage.py migrate`.

**⚠ Solo hacerlo en el template base.** Nunca en proyectos derivados que ya tengan la migración 0003 aplicada en producción.

**Esfuerzo:** 30 min · **Breaking:** No (schema final idéntico)

---

### Item 6.6 — Limpiar `.env.example` y documentar `IS_SERVER`

**Problema:** `.env.example` lista variables que el código no consume, o que no están documentadas:

- `BROKER_SERVER`, `BROKER_SERVER_PORT` — solo usadas si `USE_CELERY=True` o `USE_WEB_SOCKET=True`.
- `CLIENT_ID`, `CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` — Google OAuth pero no se documenta que son para el provider allauth.
- `BACK_URL` — definida pero no se usa en ningún settings.
- `IS_SERVER` — usada en `django_base/wsgi.py` con lógica de signal handlers + sleep; no documentada.

**Ubicación:** `.env.example`, `django_base/wsgi.py`, `readme.md`.

**Plan sugerido:**

1. Grep real de uso: para cada variable en `.env.example`, confirmar que al menos un `.py` la consume via `env(...)`.
2. Agrupar por comentarios: `# Required`, `# Optional - OAuth`, `# Optional - Celery`, etc.
3. Eliminar las que nadie consume.
4. **`IS_SERVER`**: leer `wsgi.py`, entender qué hace (parece ser un hack para graceful shutdown en algún deployment específico). Si nadie se acuerda para qué era, eliminar o documentar en el readme.

**Esfuerzo:** 1 h · **Breaking:** No

---

### Item 6.7 — Limpiar `.gitignore` duplicado

**Problema:** el `.gitignore` actual tiene patterns repetidos (dos bloques con reglas casi idénticas).

**Ubicación:** `.gitignore`

**Plan sugerido:**

1. Leer el archivo completo.
2. Consolidar en un solo bloque organizado por categorías: Python, Django, venv, IDE, Docker, OS, custom.
3. Usar un template canónico de [gitignore.io](https://gitignore.io/api/python,django,visualstudiocode,macos,windows,linux) como base y adaptar.

**Esfuerzo:** 20 min · **Breaking:** No

---

### Item 6.8 — `docker-compose.yml`: sacar `version: "3.9"` y limpiar comentarios

**Problema:**
- `version: "3.9"` es obsoleto desde Docker Compose v2 (2021). Se puede eliminar la línea.
- Bloques comentados de `redis`/`celery` (líneas 35-47) son ruido.
- `POSTGRES_NAME` en las env del `web` no matchea `DB_NAME` del `.env.example`.

**Ubicación:** `docker-compose.yml`

**Plan sugerido:**

1. Eliminar la primera línea `version: "3.9"`.
2. Eliminar los bloques comentados de redis/celery. Si alguna vez se necesitan, se agregan fresh — tenerlos comentados no ayuda.
3. Renombrar `POSTGRES_NAME` a `DB_NAME` (o a la inversa, alinear con `.env.example`).
4. Revisar `docker-compose-production.yml` por consistencia.

**Esfuerzo:** 30 min · **Breaking:** No (si se alinea con .env)

---

### Item 6.9 — Actualizar `readme.md`

**Problema:** el `readme.md` actual tiene ~700 líneas y menciona:
- `django-crontab` como si estuviera instalada (no lo está).
- Celery y websockets con instrucciones de "descomentar" (se pueden simplificar tras Fase 2).
- Runcommands como mecanismo principal (tras Fase 6.1 sería Makefile).
- Hooks manuales (tras Fase 4 sería pre-commit framework).
- Python 3.10.7 como recomendado (la realidad es 3.12 o 3.13).
- Swagger/Redoc con drf-yasg (tras Fase 5 es spectacular).

**Ubicación:** `readme.md`

**Plan sugerido:**

1. Hacer una pasada completa tras ejecutar las fases 1-5.
2. Actualizar cada sección para reflejar la realidad del momento.
3. Considerar **dividir en varios archivos**: `README.md` (quickstart de 30 líneas) + `docs/setup.md`, `docs/libraries.md`, `docs/deployment.md`, `docs/i18n.md`, etc.
4. Al menos, reordenar las secciones para poner el quickstart arriba y mover la teoría de cada librería a un apéndice.

**Esfuerzo:** 2-4 h · **Breaking:** No

---

### Item 6.10 — Consolidar `UserProfileCompleteSerializer` / `UserCompleteRegisterSerializer`

**Problema:** hay 2 serializers en `users/serializers.py` con docstrings casi idénticos:
- `UserProfileCompleteSerializer` (líneas 13-27)
- `UserCompleteRegisterSerializer` (líneas 30-48)

Son distintos (uno expone `Profile`, el otro `User` con profile anidado), pero la duplicación de intención confunde. También `UserProfileSerializer` (línea 51) y `UserProfileListSerializer` (línea 59) tienen solapamiento similar.

**Ubicación:** `users/serializers.py`

**Plan sugerido:**

1. Mapear qué endpoint usa cada serializer.
2. Renombrar para que los nombres reflejen uso: `ProfileRegisterSerializer`, `UserRegisterSerializer`, `ProfileDetailSerializer`, `UserListSerializer`.
3. Eliminar la duplicación donde exista.
4. Reemplazar el override de `to_representation` en `UserSerializer:72-75` por `read_only_fields = ("email",)` en el `Meta`.

**⚠ Verificar que el campo `email` siga saliendo en la response** tras el cambio — es un detalle observable por el front.

**Esfuerzo:** 1 h · **Breaking:** No si se mantiene la shape de response. Sí si se renombran campos.

---

### Item 6.11 — Activar `ROTATE_REFRESH_TOKENS` en simplejwt

**Problema:** `SIMPLE_JWT` configura lifetimes pero no rotación de refresh tokens. Estándar de seguridad moderno: cada refresh genera un nuevo refresh token y marca el viejo como usado (blacklist).

**Ubicación:** `django_base/settings/custom_settings.py:93-96`

**Plan sugerido:**

1. Actualizar el dict:
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=5),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

2. Agregar `"rest_framework_simplejwt.token_blacklist"` a `INSTALLED_APPS`.
3. Correr `migrate` (crea las tablas de blacklist).
4. Verificar que `POST /api/auth/token/refresh/` devuelve ahora **ambos** tokens (`access` y `refresh`, no solo `access`).

**🔴 Breaking potencial:** el front debe persistir el nuevo refresh token después de cada refresh. Si el front ya hace esto (la mayoría de clientes JWT modernos lo hacen), no hay problema. **Confirmar con el front antes de activarlo.**

**Esfuerzo:** 1 h · **Breaking:** Posible — coordinar con front.

---

### Item 6.12 — Auditar `custom_settings.py::PASSWORD_CHANGE_BY_EMAIL`

**Problema:** la configuración `PASSWORD_CHANGE_BY_EMAIL = True` fuerza que el cambio de password SOLO pueda hacerse por flow de email. Si el email del usuario está comprometido, el usuario queda atrapado.

**Ubicación:** `django_base/settings/configurations.py` + `auth/views.py:PasswordChangeViewModify`.

**Plan sugerido:**

Decisión de negocio: ¿es intencional o heredado? Opciones:

- **Mantener:** documentar claramente que el flag es por diseño y el único método permitido es via email.
- **Permitir ambos:** el endpoint `password/change/` acepta cambio directo (con `old_password`) Y también acepta el flow de email. Es más flexible.

Si se elige flexibilizar, el código ya tiene la lógica (ver `PasswordChangeViewModify.post`), solo hay que invertir la gating.

**Esfuerzo:** 30 min - 2 h · **Breaking:** Solo si se cambia el comportamiento, en cuyo caso no debería romper al front (es más permisivo).

---

### Item 6.13 — Decidir destino de celery/websockets placeholders

**Problema:** `django_base/celery.py`, `django_base/routing.py`, `django_base/consumers.py`, `django_base/middlewares.py` tienen infraestructura para Celery y Channels que **está siempre presente pero nunca activa** por default (`USE_CELERY=False`, `USE_WEB_SOCKET=False`). Es ruido constante en el repo.

**Ubicación:** `django_base/celery.py`, `routing.py`, `consumers.py`, `middlewares.py`.

**Opciones:**

1. **Opción A — Eliminar del base.** Si alguien quiere Celery o websockets, lo agrega en el proyecto derivado. El base queda más chico.
2. **Opción B — Moverlo a una rama `feature/async-ready`** y documentar en el readme cómo mergearla.
3. **Opción C — Dejarlo como está** (status quo) pero mejorar la documentación para que sea claro cómo activarlo.

La elección depende de qué tan frecuentemente se usan estos features en proyectos derivados.

**Esfuerzo:** 1-3 h · **Breaking:** No

---

### Item 6.14 — Limpiar `wsgi.py` (`IS_SERVER` lógica oscura)

**Problema:** `django_base/wsgi.py` tiene un bloque condicional con signal handlers y `sleep` dependiendo de `IS_SERVER`. No está documentado qué es esa variable ni qué problema resolvía. Parece un hack heredado.

**Ubicación:** `django_base/wsgi.py`

**Plan sugerido:**

1. Leer el archivo completo.
2. `git blame django_base/wsgi.py` para entender cuándo y por qué se agregó.
3. Preguntar en el equipo si alguien se acuerda.
4. Si no hay justificación clara, eliminar el bloque y dejar `wsgi.py` minimal (el boilerplate estándar de Django). Y eliminar `IS_SERVER` de `.env.example`.

**Esfuerzo:** 30 min · **Breaking:** Posible en deployment específico — verificar en staging antes de prod.

---

### Item 6.16 — Rediseñar campos de archivo con nombre único + validación

**Problema:** en la Fase 3 se eliminaron `CustomFileField` y `CustomImageField` de `base_models.py` porque la implementación tenía bugs (hash con `datetime.now()` no es único bajo concurrencia, marcado `# Not tested`, MD5). Pero la idea base — un campo que renombre archivos a un identificador único y aplique validaciones — sigue siendo deseable para el template.

**Ubicación nueva:** `django_base/base_utils/base_models.py` (o un módulo aparte `base_fields.py`).

**Plan sugerido:**

1. Implementar un `upload_to` callable que use `uuid.uuid4().hex` para el nombre final, preservando la extensión original:

```python
import uuid
from pathlib import Path


def unique_upload_to(subdir):
    def _wrapper(instance, filename):
        ext = Path(filename).suffix.lower()
        return f"{subdir}/{uuid.uuid4().hex}{ext}"
    return _wrapper
```

2. Para validación de tamaño y tipo, reutilizar `FileSizeValidator` que ya existe en `base_validators.py` (se mantuvo en Fase 3) y combinarlo con `FileExtensionValidator` de Django.

3. Ejemplo de uso esperado:

```python
avatar = models.ImageField(
    upload_to=unique_upload_to("avatars"),
    validators=[FileSizeValidator(max_mb=5), FileExtensionValidator(["jpg", "jpeg", "png"])],
    blank=True,
)
```

4. Documentar el patrón en el `readme.md` (o en `docs/` tras Item 6.15).

**Por qué no se mantuvo en Fase 3:** la implementación previa tenía bugs reales (no era "preservable"); reescribirla como feature mezcla scope con la poda. Acá queda como tarea independiente cuando se quiera ofrecer un patrón canónico de upload en el template.

**Esfuerzo:** 1-2 h · **Breaking:** No (es opt-in para modelos nuevos)

---

### Item 6.17 — Resolver warnings de ruff pendientes de Fase 4

**Problema:** tras la primera corrida de `ruff check --fix` quedaron 4 warnings que requieren juicio humano:

- 2× `UP031` en `django_base/base_utils/base_viewsets.py:54-57` — `assert` con `%` formatting. Reemplazar por f-string o `.format()`.
- 2× `DJ008` (`Model does not define __str__`):
  - `platform_configurations/models.py:5` `SystemStatus`
  - `users/models.py:29` `TokenRecovery`
  Definir `__str__` razonable en cada uno (ej. `f"SystemStatus#{self.pk}"`, `f"TokenRecovery({self.user})"`).

**Esfuerzo:** 15 min · **Breaking:** No

---

### Item 6.18 — Tipado de schema OpenAPI (warnings de drf-spectacular)

**Problema:** tras la Fase 5, `manage.py spectacular --validate` reporta 4 errores únicos por views sin `serializer_class` declarado en sus actions. Los endpoints afectados quedan **ignorados** del schema generado (no aparecen en Swagger UI ni en `/api/schema/`):

- `auth/views.py:35` `PasswordRecoveryViewSet`: actions `recovery_check_token` y `recovery_confirm` sin serializer asociado.
- `platform_configurations/views.py:9` `SytemStatusViewSet` (notar el typo del nombre, ver Item 6.3) sin `serializer_class`.

**Plan sugerido:**

1. Definir serializers explícitos para cada action faltante en `PasswordRecoveryViewSet` (`recovery_check_token` → token + email; `recovery_confirm` → token + email + new_password).
2. Decorar las actions con `@extend_schema(request=..., responses=...)` de `drf_spectacular.utils` para mapearlos al schema.
3. Para `SystemStatusViewSet`: declarar `serializer_class = SystemStatusSerializer` (ya existe) o `@extend_schema_view`.
4. Re-correr `docker compose exec web python manage.py spectacular --validate` hasta `Errors: 0`.

**Esfuerzo:** 30-45 min · **Breaking:** No (solo afecta el schema generado, no las responses reales).

---

### Item 6.15 — Consolidar docs de setup

**Problema:** el setup está explicado en 3 lugares distintos (readme.md, .env.example, runcommands.py) con información parcial en cada uno y sin un quickstart de 3 pasos.

**Plan sugerido:**

Crear un `docs/quickstart.md` mínimo:

```markdown
# Quickstart

1. `cp .env.example .env` y editar valores.
2. `docker compose up -d`.
3. `make migrate && make shell`.
4. Abrir http://localhost:8000/admin (admin@admin.com / admin123123 en DEBUG).
5. Docs de la API en http://localhost:8000/api/schema/swagger-ui/.
```

Y que el `README.md` principal sea un índice de 50 líneas apuntando a subdocs.

**Esfuerzo:** 2 h · **Breaking:** No

---

## ✅ Validación general

Dado que cada item es independiente, la validación es por item. Al final de cada uno:

```bash
docker compose build web
docker compose up -d
docker compose logs web --tail=50
docker compose exec web pytest
# + curl a los endpoints que el item toca
```

---

## 📊 Checklist de cierre (marcar item por item)

- [ ] 6.1 — runcommands → Makefile
- [ ] 6.2 — rename `auth` → `auth_api`
- [ ] 6.3 — endurecer `IsSystemUpMiddleware` + fix typo `SytemStatusViewSet`
- [ ] 6.4 — tests reales (al menos cobertura mínima de auth y users)
- [ ] 6.5 — squash migraciones de `users/`
- [ ] 6.6 — limpiar `.env.example` + documentar `IS_SERVER`
- [ ] 6.7 — limpiar `.gitignore` duplicado
- [ ] 6.8 — `docker-compose.yml` sin `version:` y sin comentarios muertos
- [ ] 6.9 — actualizar `readme.md`
- [ ] 6.10 — consolidar serializers duplicados en `users/serializers.py`
- [ ] 6.11 — activar `ROTATE_REFRESH_TOKENS` (tras coordinar con front)
- [ ] 6.12 — decidir `PASSWORD_CHANGE_BY_EMAIL`
- [ ] 6.13 — destino de celery/websockets placeholders
- [ ] 6.14 — limpiar `wsgi.py`
- [ ] 6.15 — consolidar docs de setup en `docs/`
- [ ] 6.16 — rediseñar `CustomFileField`/`CustomImageField` (uuid + validators)
- [ ] 6.17 — resolver warnings de ruff pendientes de Fase 4
- [ ] 6.18 — tipado de schema OpenAPI (warnings de drf-spectacular)
- [ ] Actualizar estado de Fase 6 en `audit/README.md` a ✅ (o ✅ parcial con checklist)
