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

# --- Orquestación de subagentes (Claude Code) ---
# Requiere `claude` CLI instalado en el host. Los subagentes viven en .claude/agents/.

# Implementar una sola tarea con el builder (uso: just task tasks/01-foo.md)
# --verbose: stream de lo que hace el agente. --dangerously-skip-permissions: necesario en headless
# para que Write/Edit/Bash no se traben (en .claude/ estás en tu repo, en una rama dedicada — OK).
# Si preferís controlarlo, sacalo y allowlistá en .claude/settings.json.
task spec:
    if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
    claude -p --verbose --dangerously-skip-permissions "Use the Task tool with subagent_type=django-task-runner. The task spec to implement is at {{spec}}. Read it, follow the agent's instructions exactly, and report back per its 'Cómo reportar al terminar' section." 2>&1 | Tee-Object -FilePath ("logs/task-" + (Split-Path -Leaf "{{spec}}") + ".log")

# Implementar todas las tareas de una carpeta en orden alfabético (uso: just task-all tasks/)
task-all dir:
    Get-ChildItem "{{dir}}" -Filter *.md | Sort-Object Name | ForEach-Object { Write-Host "==> $($_.Name)"; just task $_.FullName }

# Revisar el diff de la rama actual contra main con el reviewer
review:
    if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
    claude -p --verbose --dangerously-skip-permissions "Use the Task tool with subagent_type=django-task-reviewer. Review the current branch diff against main and produce the report per its 'Formato del reporte' section." 2>&1 | Tee-Object -FilePath "logs/review.log"
