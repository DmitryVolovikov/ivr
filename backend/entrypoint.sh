#!/bin/sh
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-rag}

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; do
  echo "Waiting for Postgres at $DB_HOST:$DB_PORT..."
  sleep 2
done

echo "Postgres is ready"

cd /app
export PYTHONPATH=/app

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
