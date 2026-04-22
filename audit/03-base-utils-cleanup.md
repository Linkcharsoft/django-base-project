# Fase 3 — Poda de `django_base/base_utils/`

**Esfuerzo:** 2 h · **Riesgo:** Bajo · **Breaking para el front:** No

---

## 📌 Contexto

`django_base/base_utils/` tiene ~8 archivos con clases y funciones "base" reutilizables. Auditado con grep en todo el repo, **alrededor del 50% es código huérfano** (nunca referenciado), incluye anti-patrones y tiene cosas sin testear ("Not tested" marcado en comentarios). Esta fase elimina lo muerto y arregla lo que queda.

Antes de empezar leé [README.md](./README.md) para contexto general del proyecto.

**Prerequisito:** idealmente ejecutar **después de la Fase 1** (así no mezclás limpieza con fixes de seguridad). Es independiente de la Fase 2.

---

## 🎯 Objetivo

- Eliminar ~600 líneas de código huérfano o anti-patrón en `base_utils/`.
- Reducir la superficie de `CustomPagination` (actualmente permite DoS por paginación con `max_page_size = 999999`).
- Mantener lo que **sí está en uso**: `BaseModel`, `base_viewsets.py`, `base_validators.py`, `BaseSerializer`, 3 funciones de `utils.py`.

---

## 📂 Archivos afectados

| Archivo | Acción |
|---|---|
| `django_base/base_utils/base_models.py` | Podar: dejar solo `BaseModel` |
| `django_base/base_utils/base_pagination.py` | Reemplazar `CustomPagination` por variante con `max_page_size = 100` |
| `django_base/base_utils/base_views.py` | **ELIMINAR** archivo completo |
| `django_base/base_utils/base_tests.py` | **ELIMINAR** archivo completo |
| `django_base/base_utils/base_serializers.py` | Dejar solo `BaseSerializer`, remover `BaseSoftDeleteSerializer` |
| `django_base/base_utils/utils.py` | Podar: dejar solo 3 funciones en uso |
| `django_base/base_utils/base_validators.py` | **MANTENER tal cual** (está en uso) |
| `django_base/base_utils/base_viewsets.py` | **MANTENER tal cual** (muy usado) |

---

## 🔍 Pre-check

Correr estos greps para confirmar que no hay drift desde el análisis:

```bash
# 1. BaseSoftDeleteModel: confirmar que nadie lo usa
grep -rn "BaseSoftDeleteModel" --include="*.py" .
# Esperado: solo la definición en base_models.py

# 2. BaseUserCustomManager: confirmar que nadie lo usa
grep -rn "BaseUserCustomManager" --include="*.py" .
# Esperado: solo la definición en base_models.py

# 3. CustomFileField / CustomImageField: confirmar que nadie los usa
grep -rn "CustomFileField\|CustomImageField" --include="*.py" .
# Esperado: solo las definiciones en base_models.py

# 4. TokenProtectedViewMixin / TokenProtectedAPIView
grep -rn "TokenProtectedViewMixin\|TokenProtectedAPIView" --include="*.py" .
# Esperado: solo las definiciones en base_views.py

# 5. NoMediaTestCase
grep -rn "NoMediaTestCase" --include="*.py" .
# Esperado: solo la definición en base_tests.py

# 6. BaseSoftDeleteSerializer
grep -rn "BaseSoftDeleteSerializer" --include="*.py" .
# Esperado: solo la definición en base_serializers.py

# 7. Funciones de utils.py candidatas a eliminar
grep -rn "get_date_with_timezone\|check_required_fields\|check_fields_options" --include="*.py" .
# Esperado: solo las definiciones

# 8. Funciones de utils.py a mantener (confirmar uso)
grep -rn "get_random_string\|get_default_for_email_template\|email_template_sender" --include="*.py" .
# Esperado: referencias en auth/views.py (imports)

# 9. CustomPagination
grep -rn "CustomPagination" --include="*.py" .
# Esperado: definición + uso en custom_settings.py (DEFAULT_PAGINATION_CLASS)

# 10. BaseModel / BaseSerializer / BaseGenericViewSet (confirmar uso, NO eliminar)
grep -rn "BaseModel\b" --include="*.py" .
grep -rn "BaseSerializer\b" --include="*.py" .
grep -rn "BaseGenericViewSet" --include="*.py" .
```

Si alguna de las candidatas a eliminar **sí tiene referencias nuevas**, saltar esa eliminación y documentar.

---

## 🔧 Plan de ejecución

### Paso 1 — Podar `base_models.py`

**Estado actual:** 65 líneas con `BaseCustomManager`, `BaseUserCustomManager`, `BaseModel`, `BaseSoftDeleteModel`, `CustomFileField`, `CustomImageField`.

**Qué dejar:** solo `BaseModel` (usado por `User` y `Profile` en `users/models.py`).

**Nuevo contenido completo:**
```python
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

**Por qué se eliminan los demás:**
- `BaseCustomManager` + `BaseSoftDeleteModel`: soft-delete definido pero ningún modelo hereda de él. Si en el futuro se necesita, usar `django-safedelete` (mantenido).
- `BaseUserCustomManager`: combinaba soft-delete + UserManager, pero `User` nunca lo usa.
- `CustomFileField`/`CustomImageField`: cero referencias; además usan `datetime.now()` para el hash (no es único si suben 2 archivos en el mismo microsegundo) y el comentario dice `# Not tested`. Si se necesita, usar `uuid.uuid4().hex` directamente en el `upload_to` callable.

---

### Paso 2 — Endurecer `base_pagination.py`

**Estado actual:**
```python
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 999999
```

**Problema:** `max_page_size = 999999` permite que cualquier cliente pida `?page_size=999999` y mate la DB con un SELECT masivo. Es un vector de DoS trivial.

**Nuevo contenido:**
```python
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
```

**Impacto:** el valor default (`PAGE_SIZE = 10`) no cambia. Lo único que cambia es el techo cuando el cliente pasa `page_size` explícito. Si el frontend pasa `page_size=50` sigue funcionando. Si pasa `page_size=5000`, antes iba; ahora queda clampeado a 100.

**🔴 Verificar con el front:** ¿alguna vista del template del front pide páginas más grandes de 100? Si sí, subir el techo a un valor razonable (500 máximo). Si no, dejar en 100.

---

### Paso 3 — Eliminar `base_views.py`

**Archivo completo a borrar:** `django_base/base_utils/base_views.py`

Contenía `TokenProtectedViewMixin` y `TokenProtectedAPIView`, que validaban un token pasado en query params. Cero uso en el código, además es anti-patrón (tokens en query params quedan en logs de servidor, access logs, browser history).

```bash
rm django_base/base_utils/base_views.py
```

---

### Paso 4 — Eliminar `base_tests.py`

**Archivo completo a borrar:** `django_base/base_utils/base_tests.py`

Contenía `NoMediaTestCase` que hacía override de `MEDIA_ROOT` a temp. Cero uso (los `tests.py` del proyecto están vacíos). Django 5.2 tiene `override_settings` y `tempfile.TemporaryDirectory` que son más explícitos.

```bash
rm django_base/base_utils/base_tests.py
```

---

### Paso 5 — Podar `base_serializers.py`

**Estado actual:** contiene `BaseSerializer` y `BaseSoftDeleteSerializer`.

**Qué dejar:** solo `BaseSerializer` (usado en `users/serializers.py`).

**Revisar:** leer el archivo actual y eliminar la clase `BaseSoftDeleteSerializer` manteniendo `BaseSerializer` sin cambios.

```bash
# Antes de editar, leer el archivo para confirmar estructura exacta
cat django_base/base_utils/base_serializers.py
```

---

### Paso 6 — Podar `utils.py`

**Estado actual (67 líneas):** 7 funciones — `get_random_string`, `get_date_with_timezone`, `check_required_fields`, `check_fields_options`, `check_required_fields_options`, `get_default_for_email_template`, `email_template_sender`.

**Qué dejar:**
- `get_random_string` — usada en `auth/views.py` para generar tokens.
- `get_default_for_email_template` — usada en `auth/views.py`.
- `email_template_sender` — usada en `auth/views.py`.

**Qué eliminar:**
- `get_date_with_timezone` — cero uso; además `timezone.make_aware()` de Django hace exactamente lo mismo en una línea.
- `check_required_fields` — cero uso; DRF Serializers validan esto solos.
- `check_fields_options` — cero uso; DRF `ChoiceField` lo hace mejor.
- `check_required_fields_options` — cero uso.

**Nuevo contenido completo:**
```python
import random
import string

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings


def get_random_string(length):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def get_default_for_email_template():
    return {
        "banner_url": settings.BASE_EMAILS_BANNER_URL,
        "site_name": settings.APP_NAME,
        "year": timezone.now().year,
    }


def email_template_sender(
    subject,
    template_name,
    context,
    to_email,
    from_email=settings.DEFAULT_FROM_EMAIL,
    attachments=None,
):
    context.update(get_default_for_email_template())
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=[to_email], from_email=from_email)
    email.content_subtype = "html"
    if attachments:
        for attachment in attachments:
            email.attach_file(attachment)
    email.send()
```

> **Seguridad:** `get_random_string` usa `random` (no criptográfico). Como se usa para tokens de password recovery, idealmente debería ser `secrets.token_urlsafe()`. Esto cae en la categoría de **mejora de seguridad opcional** — lo dejamos documentado pero no forzado en esta fase para no tocar el tamaño del token que genera (el front podría depender del largo). Si se quiere hacer el cambio acá, reemplazar por:
> ```python
> import secrets
>
> def get_random_string(length):
>     # Genera un token urlsafe, recortado al largo deseado
>     return secrets.token_urlsafe(length)[:length]
> ```

---

### Paso 7 — Dejar intactos (verificar)

Estos archivos **no se tocan** en esta fase; solo confirmar que siguen como estaban:

- `django_base/base_utils/base_validators.py` — `UpperValidator`, `SymbolValidator`, `NumberRequiredValidator`, `FileSizeValidator`. Están en uso activo en `AUTH_PASSWORD_VALIDATORS` (via `custom_settings.py`) y tienen i18n en `locale/en/LC_MESSAGES/django.po`.
- `django_base/base_utils/base_viewsets.py` — `NoPutViewSetMixin`, `ViewSetPermissionMixin`, `ViewSetSerializerMixin`, `BaseGenericViewSet`, `BaseReadOnlyModelViewSet`, `BaseModelViewSet`. Muy usados por `users/views.py` y `auth/views.py`. Bien implementados.

---

## ✅ Validación

```bash
# 1. Arranque limpio
docker compose restart web
docker compose logs web --tail=50

# 2. Verificar que los imports siguen resolviendo
docker compose exec web python manage.py shell -c "
from django_base.base_utils.base_models import BaseModel
from django_base.base_utils.base_serializers import BaseSerializer
from django_base.base_utils.base_viewsets import BaseGenericViewSet
from django_base.base_utils.base_validators import UpperValidator, SymbolValidator
from django_base.base_utils.base_pagination import CustomPagination
from django_base.base_utils.utils import get_random_string, email_template_sender, get_default_for_email_template
print('all imports OK')
"

# 3. Verificar que los símbolos eliminados YA NO existen
docker compose exec web python -c "
try:
    from django_base.base_utils.base_models import BaseSoftDeleteModel
    print('FAIL: BaseSoftDeleteModel todavía existe')
except ImportError:
    print('OK: BaseSoftDeleteModel eliminado')
"

# 4. Tests
docker compose exec web pytest

# 5. Endpoints core responden
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/admin/login/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/swagger/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/auth/login/ -X POST -d '{}'

# 6. Paginación clampeada
# (requiere JWT admin)
# curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/users/?page_size=5000"
# → debería devolver máximo 100 ítems por página
```

---

## ⚠️ Riesgos

| Riesgo | Mitigación |
|---|---|
| Alguna rama de desarrollo activa usa una clase huérfana | El pre-check con grep cubre `main`; avisar en el canal interno antes de mergear. |
| `max_page_size = 100` corta una vista del front que pide más | Preguntar al front; si pide hasta 500, ajustar el tope. |
| `get_random_string` con `secrets` cambia el formato del token | **No aplicar el cambio opcional en esta fase** si no se coordina con el front. |

**A quién avisar:**
- 🟡 Front — confirmar que no piden `page_size` > 100 en ninguna vista.
- 🟢 Resto del equipo backend — avisar en canal interno que se podaron símbolos huérfanos.

---

## 📊 Checklist de cierre

- [ ] Pre-check con grep completo (todos los símbolos a eliminar siguen huérfanos)
- [ ] `base_models.py` podado → solo `BaseModel`
- [ ] `base_pagination.py` → `max_page_size = 100` (o el valor acordado con front)
- [ ] `base_views.py` eliminado
- [ ] `base_tests.py` eliminado
- [ ] `base_serializers.py` → solo `BaseSerializer`
- [ ] `utils.py` podado → 3 funciones
- [ ] `base_validators.py` intacto
- [ ] `base_viewsets.py` intacto
- [ ] Imports de todos los símbolos mantenidos funcionan
- [ ] Imports de símbolos eliminados fallan correctamente
- [ ] `pytest` pasa
- [ ] Endpoints core responden
- [ ] Commit: `[ CLEAN ] Fase 3 auditoría: poda de base_utils`
- [ ] Actualizar estado de Fase 3 en `audit/README.md` a ✅
