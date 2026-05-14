# Auditoría del base — Plan de ejecución por fases

Este directorio contiene el plan de limpieza/modernización del template `django-base-project` que usamos en Linkchar. El análisis original se hizo el 2026-04-10 sobre `main @ 6d5b21b`.

Cada fase está pensada para ejecutarse en **una sesión limpia** de Claude (o de otro agente) sin necesidad de contexto previo. Cada archivo es auto-contenido: explica el problema, el plan, cómo validar y los riesgos.

---

## 🗺️ Índice

| # | Archivo | Objetivo | Estado | Esfuerzo | Riesgo |
|---|---|---|---|---|---|
| 1 | [01-critical-security.md](./01-critical-security.md) | Fix de bugs y agujeros de seguridad urgentes | ✅ Completada (commit `e2fb258`, rama `v1.3`) | 1-2 h | Bajo |
| 2 | [02-dependencies-diet.md](./02-dependencies-diet.md) | Eliminar librerías no usadas (pandas/numpy out) | ✅ Completada (rama `v1.3`) | 2-4 h | Medio |
| 3 | [03-base-utils-cleanup.md](./03-base-utils-cleanup.md) | Podar `django_base/base_utils/` huérfano | ✅ Completada (commit `70abc05`, rama `v1.3`) | 2 h | Bajo |
| 4 | [04-modern-tooling.md](./04-modern-tooling.md) | ruff + uv + pre-commit framework + pyproject | ✅ Completada (rama `v1.3`) | 3-4 h | Bajo |
| 5 | [05-api-docs-modernization.md](./05-api-docs-modernization.md) | `drf-yasg` → `drf-spectacular` | ✅ Completada (rama `v1.3`) | 4-6 h | Medio |
| 6 | [06-backlog.md](./06-backlog.md) | Backlog menor (tests, squash, readme, runcommands) | 🟡 En progreso (6.7, 6.8, 6.17 ✅ en `85e4f51`) | variable | Bajo |

Orden recomendado: **1 → 2 → 3 → 4 → 5 → 6**. Las fases 1, 2 y 3 son independientes entre sí; 4 y 5 conviene hacerlas después. La 6 es backlog libre.

---

## 📌 Contexto del proyecto (para sesiones limpias)

### Qué es este repo

Template base corporativo de **Django 5.2 + DRF** que usamos como punto de partida para proyectos nuevos. Lleva años acumulando features "por las dudas" y hay basura. Este plan poda lo inútil sin romper el contrato con el frontend (que también es un template).

### Stack principal

- **Python 3.12.3** (Dockerfile) — ojo, `requirements.txt` fue compilado con 3.13; es una inconsistencia que se resuelve en Fase 2/4.
- **Django 5.2.4**, **djangorestframework 3.16.0**
- **Auth**: `dj-rest-auth 7.0.1` + `django-allauth 65.10.0` + `djangorestframework-simplejwt 5.5.1`
- **DB**: PostgreSQL 16 (docker-compose), `psycopg[binary] 3.2.9`
- **Deploy**: Docker + `gunicorn` + `whitenoise`
- **Docs API**: `drf-spectacular 0.29.0` (OpenAPI 3.1, paths en `/api/schema/`)
- **Settings**: `split-settings` en `django_base/settings/` (5 archivos)

### Estructura

```
django_base/             # proyecto principal
  settings/              # split en 5 archivos
  base_utils/            # utilidades base (a podar en Fase 3)
  urls.py, wsgi.py, asgi.py, celery.py, routing.py, consumers.py
  middlewares.py, storage_backends.py
auth/                    # ⚠ nombre colisiona con django.contrib.auth (ver Fase 6)
  views.py urls.py models.py  # PasswordRecoveryViewSet + Google OAuth
users/                   # User custom + Profile + TokenRecovery
  models.py serializers.py views.py permissions.py filters.py adapter.py
platform_configurations/ # health check global (SystemStatus)
templates/               # templates HTML de emails (allauth + password recovery)
locale/                  # i18n (traducciones de validators y utils)
hooks/                   # pre-commit bash manual (a migrar en Fase 4)
audit/                   # ← este directorio
```

### Cómo levantar local

```bash
cp .env.example .env          # completar
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Con `DEBUG=True`, el migrate crea automáticamente un admin: `admin@admin.com / admin123123`.

---

## 🔐 Contrato con el frontend (no romper sin avisar)

El frontend es también un template que consume estos endpoints. **Cualquier cambio que toque el contrato debe comunicarse antes**. Inventario al momento del análisis:

### `/api/auth/` (definido en `auth/urls.py`)

| Método | Path | View | Notas |
|---|---|---|---|
| POST | `login/` | `dj_rest_auth.LoginView` | |
| POST | `logout/` | `dj_rest_auth.LogoutView` | |
| GET | `user/` | `dj_rest_auth.UserDetailsView` | |
| POST | `token/verify/` | `simplejwt.TokenVerifyView` | |
| POST | `token/refresh/` | `dj_rest_auth.get_refresh_view()` | |
| POST | `password/change/` | `PasswordChangeViewModify` (auth/views.py:164) | |
| POST | `password/recovery/` | `PasswordRecoveryViewSet.recovery_send_mail` | ⚠ sin throttling |
| POST | `password/recovery/check-token/` | `PasswordRecoveryViewSet.recovery_check_token` | ⚠ sin throttling |
| POST | `password/recovery/confirm/` | `PasswordRecoveryViewSet.recovery_confirm` | ⚠ sin throttling |
| * | `registration/...` | `dj_rest_auth.registration.urls` | |
| * | `allauth/...` | `allauth.urls` | |
| POST | `dj-rest-auth/google/` | `GoogleLogin` | Google OAuth2 |

### `/api/users/` (definido en `users/urls.py` — router DRF)

| Método | Path | Acción | Permisos | Notas |
|---|---|---|---|---|
| GET | `users/` | `list` | `IsAdminUser` | |
| GET | `users/{id}/` | `retrieve` | `IsAuthenticated` | `{id}` puede ser `"me"` |
| PATCH | `users/{id}/` | `partial_update` | `HasRegisterCompletePermission` | |
| DELETE | `users/{id}/` | `destroy` | `IsAdminUser` | |
| PATCH | `users/complete-register/` | `complete_register` | `IsAuthenticated` | Custom action |
| PATCH | `users/{id}/toggle-block/` | `toggle_block` | `IsAdminUser` | ⚠ bug lógico interno |
| DELETE | `users/delete-test-users/` | `delete_test_users` | 🔴 `AllowAny` | **INSEGURO — Fase 1** |

### Otros endpoints montados en `django_base/urls.py`

- `admin/` — Django admin.
- `__debug__/` — debug_toolbar (⚠ montado sin gating por `DEBUG` — Fase 1).
- `api/schema/`, `api/schema/swagger-ui/`, `api/schema/redoc/` — drf-spectacular (OpenAPI 3.1).
- `api/system-status/is-system-up/` — health check (⚠ hardcoded en `platform_configurations/middlewares.py`, no tocar).
- `api/` — incluye routers de `users`, `platform_configurations`, `django_global_places` (🗑 Fase 2), `notifications` (🗑 Fase 2).

### Regla general

- 🟢 Refactors internos, throttling, logging, permisos más restrictivos sobre endpoints admin → **OK sin avisar**.
- 🟡 Cambios en responses (status codes nuevos, campos opcionales agregados) → avisar al front.
- 🔴 Cambios en paths, métodos, campos requeridos, estructura de respuesta → **breaking, avisar y coordinar**.

---

## 📖 Cómo usar este plan en una sesión limpia

Cada fase sigue la misma estructura:

1. **Contexto** — resumen auto-contenido para arrancar sin historial.
2. **Objetivo** — qué se logra.
3. **Archivos afectados** — lista exacta con line numbers.
4. **Pre-check** — qué verificar antes de tocar (para detectar drift si pasó tiempo desde el análisis).
5. **Plan** — pasos numerados con código concreto.
6. **Validación** — cómo comprobar que funciona.
7. **Riesgos / breaking changes** — qué puede romper y a quién hay que avisar.
8. **Estimación** — tiempo aproximado.

### Para arrancar una fase

1. Abrí una sesión nueva de Claude Code en la raíz del repo.
2. Decile: **"Vamos a ejecutar la Fase N del plan en `audit/0N-*.md`. Leélo, revisá el pre-check, y proponeme un plan de trabajo antes de tocar nada."**
3. Revisá el plan que te devuelve; si pinta bien, dale luz verde.
4. Al terminar, pedile que actualice el estado de la fase en este README (columna "Estado").

### Importante

- **No hacer dos fases simultáneas en la misma sesión** — se ensucia el contexto y es difícil validar.
- **Commit al final de cada fase** — idealmente con un PR separado.
- **Correr tests antes y después** de cada fase: `docker compose exec web pytest` (los tests están casi vacíos, pero el harness al menos verifica que el proyecto arranca).
- **Correr `docker compose build && up -d && logs web`** al final de cada fase para asegurar que la imagen sigue armando y el server arranca.

---

## ⚠️ Drift warning

Este plan se escribió el 2026-04-10 sobre `main @ 6d5b21b`. Si pasó mucho tiempo, antes de ejecutar una fase verificá con `git log --oneline audit/` y `git log --oneline <archivos relevantes>` si el contexto cambió. Cada fase tiene su propio **Pre-check** con los greps necesarios para detectar drift.

---

## 📝 Resumen ejecutivo

- **3 bugs/agujeros de seguridad reales** que hay que arreglar ya → Fase 1.
- **4 librerías eliminables** que arrastran pandas+numpy (~150 MB) → Fase 2.
- **~600 líneas de código huérfano** en `base_utils/` → Fase 3.
- **3 herramientas reemplazables** por versiones modernas (black→ruff, pip-tools→uv, hooks manuales→pre-commit) → Fase 4.
- **drf-yasg descatalogado** a reemplazar por drf-spectacular → Fase 5.
- **Contrato con el front es mayormente salvable** — solo el endpoint `delete-test-users` es breaking real.
- El proyecto **no necesita reescritura**, solo una poda disciplinada.
