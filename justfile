set dotenv-load := true
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

web := "web"
db := "db"

# Listar todos los targets disponibles
default:
    @just --list

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

# --- Subagent orchestration (Claude Code) ---
# Requires the `claude` CLI on the host. Subagents live under .claude/agents/.
# Permissions are defined in .claude/settings.json (tool + bash allowlist).

# Run the builder loop over tasks.md until empty or stalled (logs/run-tasks-*.log)
task-run:
    pwsh -NoProfile -File scripts/run-tasks.ps1

# Pretty-print a saved stream-json log (usage: just task-log logs/run-tasks-XXXXXX.log)
task-log path:
    pwsh -NoProfile -File scripts/pretty-log.ps1 -Path "{{path}}"

# Run reviewer against current branch diff vs main (output to logs/review.log)
review:
    if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
    pwsh -NoProfile -Command "& claude -p --verbose --output-format stream-json --verbose --include-partial-messages 'Use the Task tool with subagent_type=django-task-reviewer. Review the current branch diff against main and produce the report per its Report format section.' *> logs/review.log"
