# Fase 1 — Seguridad crítica y bugs urgentes

**Esfuerzo:** 1-2 h · **Riesgo:** Bajo · **Breaking para el front:** Solo 1 endpoint (`delete-test-users`)

---

## 📌 Contexto

El base acumuló bugs reales y pequeños agujeros de seguridad. Todos están confirmados en el código del commit `6d5b21b` (2026-04-10). Ninguno requiere rediseño; son fixes puntuales. Esta fase **no toca el contrato con el frontend** salvo en un punto explícito (endpoint `delete-test-users`, que casi con certeza el front no usa — confirmar antes).

Antes de empezar leé [README.md](./README.md) para contexto general del proyecto y el inventario de endpoints públicos.

---

## 🎯 Objetivo

Dejar el base sin bugs críticos, sin rutas de debug expuestas en producción, con rate limiting en los flows de password recovery, y con logging real (no `print`).

---

## 📂 Archivos afectados

| Archivo | Líneas relevantes | Qué se toca |
|---|---|---|
| `django_base/asgi.py` | 10 | Settings module hardcoded mal |
| `django_base/urls.py` | 37-40 | `__debug__/` sin gating por DEBUG |
| `django_base/settings/django_settings.py` | 22, 43 | `debug_toolbar` en apps y middleware sin gating |
| `django_base/settings/custom_settings.py` | 111, 158-168, 188-203 | CORS duplicado, DRF throttling, Sentry raise |
| `users/views.py` | 65, 125-149, 151-154 | `AllowAny` en `delete_test_users`, bug en `toggle_block` |
| `users/permissions.py` | 11-15 | `profile` sin null-check |
| `auth/views.py` | 111-113, 130-132, 154-156 | `print(e)` por logger |

---

## 🔍 Pre-check (leer antes de tocar)

Correr estos greps y confirmar que el drift no cambió la situación:

```bash
# 1. Confirmar mysite hardcoded en asgi
grep -n "mysite.settings" django_base/asgi.py

# 2. Confirmar debug_toolbar en urls sin if DEBUG
grep -n "__debug__" django_base/urls.py
grep -n "debug_toolbar" django_base/settings/django_settings.py

# 3. Confirmar AllowAny en delete_test_users
grep -n "delete_test_users" users/views.py
grep -n "AllowAny" users/views.py

# 4. Confirmar print(e) en auth/views.py
grep -n "print(e)" auth/views.py

# 5. Confirmar permission sin null-check
grep -n "profile.is_register_complete" users/permissions.py
```

Si alguno ya fue arreglado, saltealo y ajustá el plan.

---

## 🔧 Plan de ejecución

### Fix 1.1 — `asgi.py` settings module

**Archivo:** `django_base/asgi.py:10`

**Estado actual:**
```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
```

**Fix:**
```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_base.settings")
```

**Por qué:** el string `"mysite.settings"` es el default del tutorial de Django, nunca se arregló. Si alguien levanta ASGI/Daphne (websockets), el proceso revienta antes de arrancar.

---

### Fix 1.2 — Gatear `debug_toolbar` por DEBUG

**Archivos:**
- `django_base/settings/django_settings.py:22` (INSTALLED_APPS)
- `django_base/settings/django_settings.py:43` (MIDDLEWARE)
- `django_base/urls.py:37-40` (urlpatterns)

**Problema:** actualmente `debug_toolbar` se instala, middleware se engancha, y la URL `__debug__/` se monta **sin importar `DEBUG`**. Aunque `INTERNAL_IPS` restringe el render del panel, el middleware corre en cada request en prod y la superficie queda expuesta.

**Fix en `django_base/settings/django_settings.py`:**

1. Remover `"debug_toolbar"` del `BASE_APPS` hardcoded (línea 22).
2. Remover `"debug_toolbar.middleware.DebugToolbarMiddleware"` del `MIDDLEWARE` (línea 43).
3. Al final del archivo, agregar gating por `DEBUG` (pero `DEBUG` se define en `environment_variables.py`). La forma más limpia es hacerlo en `custom_settings.py` donde ya se lee `USE_DEBUG_TOOLBAR`:

**En `django_base/settings/custom_settings.py`**, reemplazar el bloque actual:

```python
if USE_DEBUG_TOOLBAR:
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "0.0.0.0"]
```

Por:

```python
if USE_DEBUG_TOOLBAR:
    import socket

    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
    MIDDLEWARE = MIDDLEWARE + ["debug_toolbar.middleware.DebugToolbarMiddleware"]

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "0.0.0.0"]
```

> Nota: `INSTALLED_APPS` se arma en `django_settings.py` como `THIRD_APPS + MY_APPS + BASE_APPS` — pero `django_settings.py` se importa antes que `custom_settings.py`, así que esta re-asignación funciona.

**Fix en `django_base/urls.py`** — envolver el include de debug_toolbar:

```python
from django.conf import settings

# fmt: off
urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
```

**Validación:** con `DEBUG=False` y `USE_DEBUG_TOOLBAR=False`, arrancar el server y chequear que `/__debug__/` devuelve 404.

---

### Fix 1.3 — `delete_test_users` con `AllowAny` 🔴 BREAKING

**Archivo:** `users/views.py:65, 151-154`

**Estado actual:**
```python
permissions = {
    ...
    "delete_test_users": [AllowAny],
    ...
}

@action(detail=False, methods=["DELETE"], url_path="delete-test-users")
def delete_test_users(self, request):
    get_user_model().objects.filter(is_test_user=True).delete()
    return Response(_("Test users deleted"), status=status.HTTP_204_NO_CONTENT)
```

**Problema:** cualquiera en internet puede borrar todos los usuarios marcados como `is_test_user=True`. En el template base es "solo para testing" pero cuando se deriva un proyecto real esto se olvida y queda expuesto.

**Opciones de fix (elegir una):**

**Opción A — Restringir a admin (recomendada si el front de tests lo usa):**
```python
"delete_test_users": [IsAdminUser],
```

**Opción B — Eliminar el endpoint y hacerlo management command:**
1. Borrar el método `delete_test_users` de `users/views.py` y la entrada del dict `permissions`.
2. Crear `users/management/commands/delete_test_users.py`:

```python
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Delete all users marked as is_test_user=True"

    def handle(self, *args, **options):
        deleted, _ = get_user_model().objects.filter(is_test_user=True).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} test users"))
```

Uso: `docker compose exec web python manage.py delete_test_users`.

**Antes de ejecutar:** ⚠ **confirmar con el equipo de frontend** que no están usando `DELETE /api/users/delete-test-users/` desde el template del front. Si lo usan (improbable), ir por Opción A.

---

### Fix 1.4 — Bug lógico en `toggle_block`

**Archivo:** `users/views.py:125-149`

**Estado actual:**
```python
@action(detail=True, methods=["PATCH"], url_path="toggle-block")
def toggle_block(self, request, pk=None):
    user = self.get_object()
    if not (is_active := request.data.get("is_active")):
        return Response(
            {"detail": _("is_active field is required")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        user.is_active = is_active
        user.save()
    except Exception as e:
        return Response(
            {"detail": _("is_active field should be boolean")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        (
            _("User is blocked")
            if is_active.lower() == "false"
            else _("User is unblocked")
        ),
        status=status.HTTP_200_OK,
    )
```

**Problemas:**
1. `if not (is_active := ...)` — si el front manda `is_active: false` (bool), el walrus guarda `False` y entra al branch de "falta el campo". **Nunca se puede bloquear a nadie con bool real.**
2. Línea 145: `is_active.lower()` explota si `is_active` es bool.
3. `except Exception` es demasiado amplio.

**Fix:**
```python
@action(detail=True, methods=["PATCH"], url_path="toggle-block")
def toggle_block(self, request, pk=None):
    user = self.get_object()
    is_active = request.data.get("is_active")

    if is_active is None:
        return Response(
            {"detail": _("is_active field is required")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(is_active, str):
        if is_active.lower() in ("true", "1"):
            is_active = True
        elif is_active.lower() in ("false", "0"):
            is_active = False
        else:
            return Response(
                {"detail": _("is_active field should be boolean")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not isinstance(is_active, bool):
        return Response(
            {"detail": _("is_active field should be boolean")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.is_active = is_active
    user.save(update_fields=["is_active"])

    return Response(
        _("User is unblocked") if is_active else _("User is blocked"),
        status=status.HTTP_200_OK,
    )
```

> Esto **no cambia el contrato**: acepta tanto bool como string, que es más permisivo, no menos.

---

### Fix 1.5 — `HasRegisterCompletePermission` null-safe

**Archivo:** `users/permissions.py:11-15`

**Estado actual:**
```python
def has_permission(self, request, view):
    return (
        request.user.is_authenticated and request.user.profile.is_register_complete
    )
```

**Problema:** `Profile` se crea en el `post_save` signal de `User` (ver `users/models.py:37-44`), pero si por cualquier razón el Profile no existe (edge case, signal falló, user creado por un fixture), acceder a `request.user.profile` levanta `Profile.DoesNotExist` → 500.

**Fix:**
```python
def has_permission(self, request, view):
    if not request.user.is_authenticated:
        return False
    profile = getattr(request.user, "profile", None)
    return bool(profile and profile.is_register_complete)
```

---

### Fix 1.6 — `print(e)` por logging

**Archivo:** `auth/views.py:111-113, 130-132, 154-156`

**Estado actual:**
```python
except Exception as e:
    print(e)
    pass
```

**Problema:** `print` no llega a Sentry, no llega a archivos de log, queda sepultado en stdout del contenedor. Silencia errores reales.

**Fix:** arriba del archivo (después de los imports):
```python
import logging

logger = logging.getLogger(__name__)
```

Reemplazar los 3 bloques `print(e)` por `logger.exception("<contexto descriptivo>")`:

- Línea 111 (en `recovery_send_mail`):
  ```python
  except Exception:
      logger.exception("Failed to send password recovery email")
  ```

- Línea 130 (en `recovery_check_token`):
  ```python
  except Exception:
      logger.exception("Failed to validate recovery token")
      return Response(_("Token is invalid"), status=status.HTTP_400_BAD_REQUEST)
  ```

- Línea 154 (en `recovery_confirm`):
  ```python
  except Exception:
      logger.exception("Failed to confirm password recovery")
      return Response(_("Token is invalid"), status=status.HTTP_400_BAD_REQUEST)
  ```

> `logger.exception(...)` incluye automáticamente el traceback — no hace falta pasar `e`.

---

### Fix 1.7 — Throttling en password recovery

**Problema:** los 3 endpoints de `/api/auth/password/recovery/*` no tienen rate limiting. Permite:
- Email enumeration si el tiempo de respuesta difiere con usuario existente vs no.
- Fuerza bruta sobre tokens de recovery (strings de 25 chars, pero igual).

**Fix — opción global simple (recomendada para el base):**

En `django_base/settings/custom_settings.py`, agregar al dict `REST_FRAMEWORK`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "dj_rest_auth.jwt_auth.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "django_base.base_utils.base_pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "password_recovery": "5/hour",
    },
}
```

Luego en `auth/views.py`, agregar a `PasswordRecoveryViewSet`:

```python
class PasswordRecoveryViewSet(BaseGenericViewSet):
    queryset = User.objects.all()
    permissions = {
        "default": [AllowAny],
    }
    throttle_scope = "password_recovery"
    ...
```

> `throttle_scope` hace que las 3 acciones del viewset compartan el mismo bucket de 5/hora por IP. **No cambia el contrato**: el único efecto visible es un 429 después de 5 intentos/hora.

**Validación:** disparar 6 POST a `/api/auth/password/recovery/` desde la misma IP en una hora — el 6° debe devolver 429.

---

### Fix 1.8 (opcional) — Sentry raise → warning

**Archivo:** `django_base/settings/custom_settings.py:188-192`

**Estado actual:**
```python
if IS_PRODUCTION:
    import sentry_sdk

    if not SENTRY_DSN:
        raise Exception("SENTRY_DSN not found in environment variables")
    ...
```

**Problema:** romper el arranque del server en producción porque falta Sentry es agresivo. Es mejor un warning + seguir.

**Fix:**
```python
if IS_PRODUCTION:
    import logging

    if not SENTRY_DSN:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN not set in production — error tracking disabled"
        )
    else:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
```

---

## ✅ Validación

Correr secuencialmente:

```bash
# 1. Arranque limpio
docker compose down
docker compose build
docker compose up -d
docker compose logs web --tail=50   # que no haya errores de import

# 2. Migrate y tests
docker compose exec web python manage.py migrate
docker compose exec web pytest    # los tests están casi vacíos pero verifica el harness

# 3. Check manual de endpoints
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/login/
# → 200

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/__debug__/
# → 404 (con DEBUG=False) o 200 (con DEBUG=True)

# 4. Password recovery throttling (6 requests, el 6° debe ser 429)
for i in {1..6}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/auth/password/recovery/ \
    -H "Content-Type: application/json" \
    -d '{"email": "noexiste@test.com"}'
done
# → 200, 200, 200, 200, 200, 429

# 5. delete-test-users no debería ser accesible sin auth (Opción A) o 404 (Opción B)
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE http://localhost:8000/api/users/delete-test-users/
# → 401 (Opción A) o 404 (Opción B)

# 6. toggle-block con bool real (requiere JWT de admin)
# curl -X PATCH ... -H "Authorization: Bearer <token>" -d '{"is_active": false}'
# → 200 con "User is blocked"
```

---

## ⚠️ Riesgos y comunicación

| Cambio | Breaking para el front | A quién avisar |
|---|---|---|
| Fix 1.1-1.2, 1.5-1.8 | No | Nadie |
| Fix 1.3 (`delete-test-users`) | **Sí** (cambio de permisos o eliminación) | 🔴 Frontend team — confirmar si usan el endpoint |
| Fix 1.4 (`toggle_block`) | No (más permisivo, no menos) | Nadie |
| Fix 1.7 (throttling) | Solo si el front dispara >5 recovery/hora desde misma IP (improbable) | Nadie |

---

## 📊 Checklist de cierre

- [ ] Fix 1.1 — `asgi.py` settings
- [ ] Fix 1.2 — `debug_toolbar` gated por `USE_DEBUG_TOOLBAR`
- [ ] Fix 1.3 — `delete-test-users` (confirmado con front, opción elegida)
- [ ] Fix 1.4 — `toggle_block` acepta bool y string
- [ ] Fix 1.5 — `HasRegisterCompletePermission` null-safe
- [ ] Fix 1.6 — `print(e)` → `logger.exception`
- [ ] Fix 1.7 — throttling en password recovery
- [ ] Fix 1.8 — Sentry warning en vez de raise (opcional)
- [ ] `docker compose build && up -d && logs web` limpio
- [ ] `pytest` pasa
- [ ] Validación manual con curl
- [ ] Commit: `[ FIX ] Fase 1 auditoría: seguridad crítica y bugs`
- [ ] Actualizar estado de Fase 1 en `audit/README.md` a ✅
