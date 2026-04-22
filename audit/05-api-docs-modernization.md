# Fase 5 — Modernizar docs de la API (`drf-yasg` → `drf-spectacular`)

**Esfuerzo:** 4-6 h · **Riesgo:** Medio · **Breaking para el front:** No (si mantenemos los mismos paths)

---

## 📌 Contexto

El base usa `drf-yasg 1.21.10` para generar documentación Swagger/Redoc. Problemas:

1. **Genera OpenAPI 2.0 (Swagger 2.0)** — estándar descatalogado desde 2017.
2. Se integra con `rest_framework.schemas.coreapi.AutoSchema`, que está **deprecated desde DRF 3.12** y puede desaparecer en cualquier release.
3. Mantenimiento lento: yasg no tiene soporte oficial para DRF 3.16+, va con parches comunitarios.
4. Integración con JWT y allauth requiere hacks (ver `SWAGGER_SETTINGS` con el `SECURITY_DEFINITIONS` manual en `custom_settings.py:173-184`).

La recomendación oficial de DRF desde hace años es **`drf-spectacular`**: genera OpenAPI 3.0/3.1, soporta JWT directo, soporta hints de tipos, mejor integración con DRF moderno y mantenimiento activo.

Antes de empezar leé [README.md](./README.md) para contexto general.

**Prerequisito:** idealmente **después de Fases 2 y 4**. Las 3 pueden hacerse en el mismo sprint pero en PRs separadas.

---

## 🎯 Objetivo

- Reemplazar `drf-yasg` por `drf-spectacular` + `drf-spectacular-sidecar`.
- Mantener los paths `swagger/`, `redoc/`, `swagger.json`, `swagger.yaml` funcionales (o al menos documentar si cambian).
- Eliminar `rest_framework.schemas.coreapi.AutoSchema`.
- Eliminar `SWAGGER_SETTINGS` custom.
- Dejar la integración con JWT funcionando en el botón "Authorize" del Swagger UI.

---

## 📂 Archivos afectados

| Archivo | Acción |
|---|---|
| `requirements.in` | Reemplazar `drf-yasg` por `drf-spectacular[sidecar]` |
| `requirements.txt` | Regenerar |
| `django_base/urls.py` | Reemplazar imports y path de schema_view |
| `django_base/settings/custom_settings.py` | Eliminar `SWAGGER_SETTINGS`, eliminar `DEFAULT_SCHEMA_CLASS` coreapi, agregar `SPECTACULAR_SETTINGS` |
| `django_base/settings/django_settings.py` | Remover `"drf_yasg"` de `BASE_APPS`, agregar `"drf_spectacular"` y `"drf_spectacular_sidecar"` |
| `readme.md` | Actualizar referencias a Swagger/Redoc si algo cambia |

---

## 🔍 Pre-check

```bash
# 1. Confirmar uso actual de drf-yasg
grep -rn "drf_yasg\|drf-yasg" --include="*.py" .
# Esperado: solo en urls.py, settings/django_settings.py, settings/custom_settings.py

# 2. Confirmar que coreapi AutoSchema está configurado
grep -n "coreapi" django_base/settings/custom_settings.py

# 3. Confirmar que NO hay imports de yasg en views/serializers
grep -rn "swagger_auto_schema\|yasg" --include="*.py" auth/ users/ platform_configurations/
# Esperado: vacío. Si hay decoradores `@swagger_auto_schema` en alguna view, hay que
# convertirlos a `@extend_schema` de spectacular (no es complicado, pero agrega trabajo).

# 4. Chequear si hay algún schema custom
grep -rn "AutoSchema\|SchemaGenerator" --include="*.py" .
```

---

## 🔧 Plan de ejecución

### Paso 1 — Editar `requirements.in`

**Estado actual:**
```
...
drf-writable-nested
drf-yasg
factory_boy
...
```

**Nuevo:**
```
...
drf-spectacular[sidecar]
drf-writable-nested
...
```

> Nota: el extra `[sidecar]` instala `drf-spectacular-sidecar`, que empaqueta los assets estáticos de Swagger UI y Redoc (para no depender de CDNs externos).

**Recompilar lockfile:**
```bash
docker compose run --rm web uv pip compile --upgrade --output-file=requirements.txt requirements.in
```

(si todavía no hiciste Fase 4, usar `pip-compile` en vez de `uv pip compile`).

---

### Paso 2 — Actualizar `INSTALLED_APPS`

**Archivo:** `django_base/settings/django_settings.py`

**Estado actual (línea 20):**
```python
BASE_APPS = [
    ...
    "drf_yasg",
    "corsheaders",
    ...
]
```

**Nuevo:**
```python
BASE_APPS = [
    ...
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",
    ...
]
```

---

### Paso 3 — Reemplazar `SWAGGER_SETTINGS` y `DEFAULT_SCHEMA_CLASS`

**Archivo:** `django_base/settings/custom_settings.py`

**Estado actual:**

```python
# <---------------------- Rest configurations ---------------------->
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "dj_rest_auth.jwt_auth.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "django_base.base_utils.base_pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SITE_ID = 1

# <-------------- SWAGGER configurations -------------->
SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SHOW_REQUEST_HEADERS": True,
    "SECURITY_DEFINITIONS": {
        "api_key": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Write 'Token' in the field, followed by a space and then your token",
        }
    },
}
```

**Nuevo:**

```python
# <---------------------- Rest configurations ---------------------->
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "dj_rest_auth.jwt_auth.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "django_base.base_utils.base_pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    # Si venís de Fase 1 y agregaste throttling, mantenerlo acá.
}

SITE_ID = 1

# <-------------- drf-spectacular configurations -------------->
SPECTACULAR_SETTINGS = {
    "TITLE": "Base project API",
    "DESCRIPTION": "Base project documentation",
    "VERSION": "1.0.0",
    "CONTACT": {"email": "contact@linkchar.com"},
    "SERVE_INCLUDE_SCHEMA": False,
    # Usa assets locales (del sidecar), no CDN
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    # Hace que el botón "Authorize" funcione directo con JWT Bearer
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
}
```

---

### Paso 4 — Reemplazar `django_base/urls.py`

**Estado actual (tras Fase 2, con los routers de notifications y global_places ya sacados):**
```python
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from rest_framework.routers import DefaultRouter

from django.contrib import admin
from django.urls import path, include, re_path

from users.urls import router as users_router
from platform_configurations.urls import router as platform_configurations_router


schema_view = get_schema_view(
    openapi.Info(
        title="Base project API",
        default_version="v1",
        description="Base project documentation",
        contact=openapi.Contact(email="contact@linkchar.com"),
    ),
    public=True,
)

base_router = DefaultRouter()
base_router.registry.extend(users_router.registry)
base_router.registry.extend(platform_configurations_router.registry)



# fmt: off
#<-------------- Django + libraries urls -------------->
urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

# <-------------- Swagger urls -------------->
urlpatterns += [
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

#<-------------- Our apps includes -------------->
urlpatterns += [
    path("api/users/", include("users.urls")),
    path("api/auth/", include("auth.urls")),
]

#<-------------- Our base router -------------->
urlpatterns += [path("api/", include(base_router.urls)),]
# fmt: on
```

**Nuevo:**
```python
from rest_framework.routers import DefaultRouter

from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from users.urls import router as users_router
from platform_configurations.urls import router as platform_configurations_router


base_router = DefaultRouter()
base_router.registry.extend(users_router.registry)
base_router.registry.extend(platform_configurations_router.registry)


# fmt: off
# <-------------- Django + libraries urls -------------->
urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

# <-------------- API schema (drf-spectacular) -------------->
urlpatterns += [
    # Raw schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI - compat con el path legacy /swagger/
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Redoc - compat con el path legacy /redoc/
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# <-------------- Our apps includes -------------->
urlpatterns += [
    path("api/users/", include("users.urls")),
    path("api/auth/", include("auth.urls")),
]

# <-------------- Our base router -------------->
urlpatterns += [path("api/", include(base_router.urls))]
# fmt: on
```

**Diferencias con el anterior:**
- Los paths legacy `swagger/` y `redoc/` **se mantienen** para no romper bookmarks ni tooling interno.
- El path del schema crudo cambia: antes era `/swagger.json` y `/swagger.yaml`; ahora es `/api/schema/` (OpenAPI 3.1 JSON) o `/api/schema/?format=yaml`.
- Si algún script de CI o doc interna linkea a `/swagger.json`, hay que actualizarlo (ver "Comunicación").

> **Opción: mantener también `/swagger.json`** por compatibilidad con clientes viejos. Agregar:
> ```python
> from drf_spectacular.views import SpectacularAPIView
> urlpatterns += [path("swagger.json", SpectacularAPIView.as_view(), name="swagger-json")]
> ```
> Pero el contenido ya es OpenAPI 3.1, no Swagger 2.0 — los clientes que parseen el esquema tienen que tolerar el cambio de formato.

---

### Paso 5 — Eliminar el stub de `users/urls.py` si quedó vacío

`users/urls.py` actual termina en:
```python
router = DefaultRouter()
router.register("users", UserViewSet, basename="users")

urlpatterns = []
```

Si el `include("users.urls")` en `django_base/urls.py` no agrega nada más (porque el router se mergea en `base_router`), el `path("api/users/", include("users.urls"))` no hace nada útil. Verificar:

```bash
docker compose exec web python manage.py show_urls | grep -i users
```

Si confirmás que todas las URLs de `/api/users/...` vienen del `base_router`, podés eliminar la línea `path("api/users/", include("users.urls"))` en el nuevo `django_base/urls.py` y dejar solo el `base_router`. Esto simplifica routing pero **es opcional** y puede afectar namespace resolution; dejarlo si hay dudas.

---

### Paso 6 — Verificar decoradores en views

```bash
grep -rn "swagger_auto_schema" --include="*.py" .
```

Si aparecen, hay que convertirlos. Ejemplo de migración típica:

**Antes (yasg):**
```python
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    request_body=MySerializer,
    responses={200: MySerializer},
)
def post(self, request):
    ...
```

**Después (spectacular):**
```python
from drf_spectacular.utils import extend_schema

@extend_schema(
    request=MySerializer,
    responses={200: MySerializer},
)
def post(self, request):
    ...
```

El módulo `drf_spectacular.utils` tiene equivalentes de casi todo: `OpenApiParameter`, `OpenApiExample`, `inline_serializer`, etc. Documentación: https://drf-spectacular.readthedocs.io.

---

### Paso 7 — Generar y validar el schema

```bash
# Schema JSON crudo
docker compose exec web python manage.py spectacular --file schema.yaml
# Esto genera un schema.yaml en la raíz — revisar que no haya warnings graves

# Si hay warnings por serializers mal tipados, son oportunidades para mejorar
# el tipado, pero no bloquean esta fase. Documentar para Fase 6.

rm schema.yaml  # limpiar; no commitear
```

Para convertir el schema a diff-friendly y vigilarlo:
```bash
docker compose exec web python manage.py spectacular --validate --file schema.yaml
```

---

## ✅ Validación

```bash
# 1. Rebuild
docker compose build web
docker compose up -d
docker compose logs web --tail=50

# 2. drf-yasg fuera, drf-spectacular dentro
docker compose exec web python -c "import drf_yasg" 2>&1 | grep -q "No module" && echo "yasg out"
docker compose exec web python -c "import drf_spectacular; print('spectacular OK')"

# 3. Endpoints de docs
curl -s -o /dev/null -w "swagger/: %{http_code}\n" http://localhost:8000/swagger/
curl -s -o /dev/null -w "redoc/: %{http_code}\n" http://localhost:8000/redoc/
curl -s -o /dev/null -w "schema: %{http_code}\n" http://localhost:8000/api/schema/
# → todos 200

# 4. Verificar que el schema tiene todos los endpoints
curl -s http://localhost:8000/api/schema/ | grep -c "password/recovery"
# → >= 3 (los 3 endpoints de password recovery)

# 5. Abrir Swagger UI en el browser y:
#    - Ver que los endpoints de /api/auth/* y /api/users/* aparecen
#    - Probar el botón "Authorize" con un Bearer JWT real
#    - Disparar un request desde el UI

# 6. Tests
docker compose exec web pytest
```

---

## ⚠️ Riesgos y comunicación

| Riesgo | Mitigación |
|---|---|
| `/swagger.json` era consumido por un script de CI, postman sync, o cliente generado | **Pre-check con el equipo**: ¿alguien exporta el schema automatizadamente? Si sí, apuntarlos al nuevo `/api/schema/` y avisarles del cambio de formato (Swagger 2 → OpenAPI 3.1). |
| Decoradores `@swagger_auto_schema` dispersos en el código | Hacer grep como en el Pre-check; convertirlos uno por uno. |
| Algún serializer custom no se tipa correctamente en spectacular | spectacular emite warnings pero no rompe. Agregar `@extend_schema_field` donde haga falta, o dejarlo para Fase 6. |
| El botón Authorize de Swagger UI no funciona con JWT | Ya está cubierto con `SWAGGER_UI_SETTINGS.persistAuthorization = True`. Si el front usa un esquema de header distinto, ajustar `SECURITY_REQUIREMENTS` en `SPECTACULAR_SETTINGS`. |

**A quién avisar:**
- 🟡 Frontend: los paths `/swagger/` y `/redoc/` siguen funcionando visualmente, pero el contenido es OpenAPI 3.1 en vez de Swagger 2.0. Si el front importa el schema para generar clientes (`openapi-generator`, `orval`, etc.), tienen que actualizar su parser.
- 🟡 Equipo backend: si alguien tenía `@swagger_auto_schema` local en ramas, tiene que migrar a `@extend_schema`.

---

## 📊 Checklist de cierre

- [ ] Pre-check: grep por `drf_yasg` y `swagger_auto_schema`
- [ ] `requirements.in` — `drf-yasg` → `drf-spectacular[sidecar]`
- [ ] `requirements.txt` regenerado
- [ ] `INSTALLED_APPS` actualizado
- [ ] `SWAGGER_SETTINGS` eliminado
- [ ] `DEFAULT_SCHEMA_CLASS` cambiado a `drf_spectacular.openapi.AutoSchema`
- [ ] `SPECTACULAR_SETTINGS` agregado
- [ ] `django_base/urls.py` usando `SpectacularAPIView`/`SpectacularSwaggerView`/`SpectacularRedocView`
- [ ] Paths legacy `/swagger/` y `/redoc/` siguen respondiendo 200
- [ ] `/api/schema/` responde con OpenAPI 3.1
- [ ] Decoradores `@swagger_auto_schema` migrados (si los había)
- [ ] `manage.py spectacular --validate` sin errores críticos
- [ ] Swagger UI abre en el browser y muestra los endpoints
- [ ] Botón Authorize con JWT funciona
- [ ] `pytest` pasa
- [ ] Frontend avisado del cambio de formato de schema (si usan codegen)
- [ ] `readme.md` actualizado si menciona Swagger/Redoc
- [ ] Commit: `[ CHORE ] Fase 5 auditoría: drf-yasg → drf-spectacular`
- [ ] Actualizar estado de Fase 5 en `audit/README.md` a ✅
