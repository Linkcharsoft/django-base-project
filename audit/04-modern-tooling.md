# Fase 4 — Tooling moderno (ruff + uv + pre-commit + pyproject)

**Esfuerzo:** 3-4 h · **Riesgo:** Bajo · **Breaking para el front:** No

---

## 📌 Contexto

El base usa herramientas de tooling que en 2026 ya son consideradas "legacy" o al menos subóptimas:

- **`black`** para formatear. Cubre formato, pero no lint; no hay `flake8`, `isort`, `pyupgrade`, `pydocstyle`. Se reemplaza por `ruff` (formato + lint, ~30× más rápido, un solo binario).
- **`pip-tools` + `pip-sync`** en el Dockerfile. Funciona, pero `uv` de Astral es 10-100× más rápido y usa el mismo `requirements.in`/`requirements.txt`.
- **`move_hooks.py` + `hooks/pre-commit`** como mecanismo de hook manual en bash. Se reemplaza por el framework oficial [`pre-commit`](https://pre-commit.com).
- **`pytest.ini`** standalone. Se consolida en `pyproject.toml` junto con ruff y coverage.

Esta fase **no toca lógica de aplicación**, solo herramientas.

Antes de empezar leé [README.md](./README.md) para contexto general.

**Prerequisito:** idealmente **después de Fase 2** (para que la dieta de dependencias ya esté hecha y el lockfile regenerado).

---

## 🎯 Objetivo

- Reemplazar `black` por `ruff` (format + lint).
- Reemplazar `pip-tools` + `pip-sync` por `uv` en el Dockerfile.
- Migrar los hooks manuales de `hooks/` al framework `pre-commit`.
- Consolidar configuración (ruff, pytest, coverage) en `pyproject.toml`.
- Eliminar `move_hooks.py` y `hooks/`.
- Agregar `pip-audit` como step opcional de CI.

---

## 📂 Archivos afectados

| Archivo | Acción |
|---|---|
| `requirements.in` | Reemplazar `black` por `ruff` |
| `requirements.txt` | Regenerar |
| `Dockerfile` | Reemplazar `pip-tools`/`pip-sync` por `uv` |
| `pytest.ini` | Eliminar (se consolida en pyproject) |
| `pyproject.toml` | **Crear** con config de ruff, pytest, coverage |
| `.pre-commit-config.yaml` | **Crear** |
| `hooks/pre-commit` | Eliminar |
| `hooks/pre-push.sample` | Eliminar |
| `move_hooks.py` | Eliminar |
| `readme.md` | Actualizar sección "Hooks" y "Running Tests" |

---

## 🔍 Pre-check

```bash
# 1. Estado actual de tooling
cat pytest.ini
cat hooks/pre-commit
ls hooks/
cat move_hooks.py

# 2. Confirmar que black no está hardcoded en scripts
grep -rn "black " --include="*.py" --include="*.sh" --include="Dockerfile" .
grep -rn "black\." --include="*.py" .

# 3. Confirmar que pip-sync está en el Dockerfile
grep -n "pip-sync\|pip-tools\|pip-compile" Dockerfile
```

---

## 🔧 Plan de ejecución

### Paso 1 — Crear `pyproject.toml`

**Archivo nuevo** en la raíz del repo.

```toml
[project]
name = "django-base-project"
version = "0.1.0"
description = "Linkchar Django base template"
requires-python = ">=3.12"

# ---------- Ruff ----------
[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = [
    "migrations",
    "static",
    "media",
    ".venv",
    "venv",
]

[tool.ruff.lint]
# Empezamos permisivos y endurecemos con el tiempo
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "DJ",   # flake8-django
    "C4",   # comprehensions
    "SIM",  # simplifications
]
ignore = [
    "E501",   # line too long (el formatter se encarga)
    "B008",   # function calls in default args (Django patterns)
    "DJ001",  # Nullable CharField (lo dejamos al criterio del dev)
]

[tool.ruff.lint.per-file-ignores]
"**/migrations/*.py" = ["E", "F", "I", "UP"]
"**/settings/*.py"   = ["F401", "F403", "F405"]
"manage.py"          = ["E402"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

# ---------- Pytest ----------
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "django_base.settings"
python_files = ["test_*.py", "tests.py", "*_tests.py"]
addopts = "--reuse-db --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]

# ---------- Coverage ----------
[tool.coverage.run]
source = ["."]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/test_*.py",
    "manage.py",
    "django_base/wsgi.py",
    "django_base/asgi.py",
    "*/settings/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

> **Ajustar `target-version`:** si en la Fase 2 migraste a Python 3.13, cambiar a `py313` en `tool.ruff` y `requires-python = ">=3.13"`.

---

### Paso 2 — Eliminar `pytest.ini`

```bash
rm pytest.ini
```

Todo queda en `[tool.pytest.ini_options]` del `pyproject.toml`.

---

### Paso 3 — Reemplazar `black` por `ruff` en `requirements.in`

**Estado actual:**
```
black
...
```

**Nuevo:**
```
ruff
...
```

Luego recompilar:

```bash
# Opción A (si el Dockerfile todavía usa pip-tools, antes del Paso 4)
docker compose run --rm web bash -c "pip-compile --upgrade --output-file=requirements.txt requirements.in"

# Opción B (si ya migraste a uv en el Paso 4, hacelo después)
```

---

### Paso 4 — Migrar el Dockerfile de pip-tools a uv

**Estado actual (tras Fase 2):**
```dockerfile
...
RUN pip install --upgrade pip && pip install pip-tools

COPY requirements.txt ./
RUN pip-sync requirements.txt
...
```

**Nuevo:**
```dockerfile
...
# Instalar uv (instalador oficial, copia binario a /usr/local/bin)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY requirements.txt ./
RUN uv pip sync --system requirements.txt
...
```

**Notas:**
- `--system` le dice a `uv` que instale en el Python del sistema en vez de crear un venv (lo que queremos dentro de un contenedor).
- `uv pip sync` es equivalente directo de `pip-sync`: instala exactamente lo que dice el lockfile y quita lo que sobra.
- El multistage COPY es el método oficial recomendado por Astral para meter `uv` en un Dockerfile.

**Para recompilar `requirements.txt` con `uv`:**
```bash
docker compose run --rm web uv pip compile --upgrade --output-file=requirements.txt requirements.in
```

> `uv pip compile` es el reemplazo de `pip-compile`, misma interfaz.

---

### Paso 5 — Crear `.pre-commit-config.yaml`

**Archivo nuevo** en la raíz:

```yaml
# See https://pre-commit.com for more information
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0   # actualizar al último estable al momento de ejecutar
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/adamchainz/django-upgrade
    rev: 1.22.0
    hooks:
      - id: django-upgrade
        args: [--target-version, "5.2"]
```

**Ajustar `rev`:** cuando ejecutes, corré `pre-commit autoupdate` para pinear a las últimas releases disponibles.

---

### Paso 6 — Eliminar `hooks/` y `move_hooks.py`

```bash
rm -rf hooks/
rm move_hooks.py
```

---

### Paso 7 — Instalar y correr pre-commit

**Estos pasos los hace el dev en su máquina local, no en el contenedor** (aunque también se puede hacer en CI).

```bash
pip install pre-commit
pre-commit install       # instala .git/hooks/pre-commit apuntando al framework
pre-commit install --hook-type pre-push

# Primera corrida sobre todo el repo (puede modificar archivos)
pre-commit run --all-files
```

**Esperable en la primera corrida:** ruff va a reformatear varios archivos (comillas, imports desordenados, etc.). Revisá el diff y commiteá por separado:

```bash
git add -u
git diff --stat HEAD     # ver qué archivos cambió
git commit -m "[ STYLE ] Fase 4: primera aplicación de ruff format"
```

---

### Paso 8 — Actualizar el `readme.md`

Las secciones que hablan de "Hooks" y "Running Tests" ya no describen la realidad. Proponer reemplazo:

**Nueva sección "Hooks":**
```markdown
**Hooks**

Este proyecto usa [pre-commit](https://pre-commit.com) para correr ruff (format + lint)
antes de cada commit. Para instalarlo después del primer clone:

```bash
pip install pre-commit
pre-commit install
```

Para bypassear un commit puntual: `git commit --no-verify`.

Para correr manualmente sobre todo el repo: `pre-commit run --all-files`.
```

**Nueva sección "Running Tests":**

Cambiar las referencias a `pytest-cov` puro por el uso del `pyproject.toml` ya configurado:
```bash
pytest
pytest --cov --cov-report=html
```

---

### Paso 9 (opcional) — `pip-audit` en CI

Si hay un workflow de GitHub Actions (ver `.github.base/`), agregar un step:

```yaml
- name: Audit dependencies
  run: |
    pip install pip-audit
    pip-audit --requirement requirements.txt --strict
```

O como hook de `pre-commit` (corre en push):
```yaml
  - repo: https://github.com/pypa/pip-audit
    rev: v2.7.3
    hooks:
      - id: pip-audit
        args: [--requirement, requirements.txt]
        stages: [pre-push]
```

---

## ✅ Validación

```bash
# 1. Rebuild con nuevo Dockerfile
docker compose build --no-cache web
docker compose up -d
docker compose logs web --tail=50  # sin errores

# 2. Confirmar que ruff está instalado y black ya no
docker compose exec web python -c "import ruff" 2>/dev/null && echo "ruff OK"
docker compose exec web python -c "import black" 2>&1 | grep -q "No module" && echo "black out"

# 3. Ruff format dry-run
docker compose exec web ruff format --check .

# 4. Ruff lint
docker compose exec web ruff check .

# 5. Tests con la config de pyproject
docker compose exec web pytest

# 6. Pre-commit instalado local
pre-commit run --all-files

# 7. Endpoints core
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/admin/login/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/swagger/
```

---

## ⚠️ Riesgos y comunicación

| Riesgo | Mitigación |
|---|---|
| Primera corrida de ruff reformatea muchos archivos y ensucia el blame | Commit aislado con mensaje `[ STYLE ] primera aplicación de ruff format` — los blames posteriores se pueden rescatar con `git blame --ignore-rev`. |
| `ruff check` destapa bugs reales que black nunca vio | **Es deseable**; arreglarlos en un commit separado. Si son muchos y no son triviales, agregarlos a Fase 6. |
| `uv pip sync --system` rompe algún flow | Muy poco probable; es drop-in de `pip-sync`. Si pasa, volver temporalmente a pip-tools. |
| `django-upgrade` propone cambios agresivos | Revisar el diff con cuidado; confirmar que el target version (`5.2`) coincide con la versión instalada. |

**A quién avisar:**
- 🟢 Equipo backend: avisar que la primera corrida reformatea el repo entero y que deben rebasar sus ramas.
- 🟢 Frontend: nada, no hay cambios de runtime.

---

## 📊 Checklist de cierre

- [ ] `pyproject.toml` creado con config de ruff + pytest + coverage
- [ ] `pytest.ini` eliminado
- [ ] `requirements.in` — `black` → `ruff`
- [ ] `requirements.txt` regenerado
- [ ] `Dockerfile` — `pip-tools`/`pip-sync` → `uv`
- [ ] `.pre-commit-config.yaml` creado
- [ ] `hooks/` y `move_hooks.py` eliminados
- [ ] `pre-commit install` corrido local
- [ ] Primera corrida `pre-commit run --all-files` aplicada y commiteada aparte
- [ ] `ruff check .` sin errores críticos (o con los errores documentados para Fase 6)
- [ ] `pytest` pasa con la config nueva
- [ ] `docker compose build --no-cache` limpio
- [ ] Endpoints core responden
- [ ] `readme.md` actualizado (secciones Hooks y Running Tests)
- [ ] Commit principal: `[ CHORE ] Fase 4 auditoría: ruff + uv + pre-commit + pyproject`
- [ ] Commit separado: `[ STYLE ] Fase 4: primera aplicación de ruff format`
- [ ] Avisar al equipo backend que rebasen sus ramas
- [ ] Actualizar estado de Fase 4 en `audit/README.md` a ✅
