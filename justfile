set dotenv-load := true
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

web := "web"
db := "db"

# Listar todos los targets disponibles
default:
    @just --list

# Build de la imagen Docker
build:
    docker compose build

# Levantar los servicios en background
up:
    docker compose up -d

# Bajar los servicios
down:
    docker compose down

# Tail de los logs del web
logs:
    docker compose logs -f {{web}}

# Shell Django enriquecido (shell_plus)
shell:
    docker compose exec {{web}} python manage.py shell_plus

# bash dentro del container del web
bash:
    docker compose exec -it {{web}} /bin/bash

# Correr migraciones
migrate:
    docker compose exec {{web}} python manage.py migrate

# Generar archivos de migraciones
makemigrations:
    docker compose exec {{web}} python manage.py makemigrations

# Ejecutar cualquier `manage.py` comando (uso: just manage createsuperuser)
manage *args:
    docker compose exec {{web}} python manage.py {{args}}

# Correr la suite de tests
test:
    docker compose exec {{web}} pytest

# Coverage HTML report
coverage:
    docker compose exec {{web}} pytest --cov=. --cov-report=html

# Generar archivos de traducción (.po)
messages:
    docker compose exec {{web}} python manage.py makemessages -a --ignore=venv/*

# Compilar traducciones (.mo)
compilemessages:
    docker compose exec {{web}} python manage.py compilemessages --ignore=venv/*

# bash en el container de postgres
db-bash:
    docker compose exec -it {{db}} /bin/bash

# psql contra la DB del proyecto
psql:
    docker compose exec -it {{db}} psql -U "$DB_USER" "$DB_NAME"

# Dropear el schema public y restaurar desde un dump SQL
db-restore dump:
    docker compose exec {{db}} psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    docker cp "{{dump}}" {{db}}:/dump.sql
    docker compose exec {{db}} psql -U "$DB_USER" -d "$DB_NAME" -f /dump.sql

# Correr ruff format + ruff check sobre todo el proyecto
lint:
    docker compose exec {{web}} ruff format .
    docker compose exec {{web}} ruff check --fix .

# Validar el schema OpenAPI (drf-spectacular)
schema-validate:
    docker compose exec {{web}} python manage.py spectacular --validate --fail-on-warn

# Resolver dependencias y actualizar uv.lock (correr en host, fuera del container)
lock:
    uv lock

# Aplicar uv.lock al venv del container (dev: con grupo dev)
sync:
    docker compose exec {{web}} uv sync --frozen

# Agregar una dependencia (uso: just add django-redis  /  just add --dev pytest-mock)
add *args:
    uv add {{args}}
