#!/bin/bash
set -euo pipefail

# Variables de entorno esperadas:
#   DB_HOST   -> endpoint de la RDS (sin puerto, ej: mydb.xxxxxx.us-east-1.rds.amazonaws.com)
#   DB_PORT   -> puerto (ej: 5432)
#   DB_USER   -> usuario administrador (ej: postgres)
#   DB_PASSWORD   -> contraseña del usuario
#   DB_NAME   -> nombre de la nueva base a crear

if [ -z "${DB_HOST:-}" ] || [ -z "${DB_PORT:-}" ] || [ -z "${DB_USER:-}" ] || [ -z "${DB_PASSWORD:-}" ] || [ -z "${DB_NAME:-}" ]; then
  echo "❌ Missing required environment variables: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME"
  exit 1
fi

export PGPASSWORD="$DB_PASSWORD"
export LANGGRAPH_DB="langgraph_$DB_NAME"

echo "Creating database $LANGGRAPH_DB on host $DB_HOST..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$LANGGRAPH_DB\";"

echo "✅ Database $LANGGRAPH_DB created successfully."
