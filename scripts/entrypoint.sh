#!/bin/sh
set -eu

attempt=1
max_attempts="${SLOTBRIDGE_DATABASE_WAIT_ATTEMPTS:-60}"
until python -c "from sqlalchemy import text; from app.database import engine; connection = engine.connect(); connection.execute(text('SELECT 1')); connection.close()"; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "PostgreSQL did not become ready after $max_attempts attempts." >&2
    exit 1
  fi
  echo "Waiting for PostgreSQL ($attempt/$max_attempts)..."
  attempt=$((attempt + 1))
  sleep 2
done

alembic upgrade head

host="${SLOTBRIDGE_HOST:-0.0.0.0}"
port="${PORT:-${SLOTBRIDGE_PORT:-8000}}"
case "$port" in
  ''|*[!0-9]*)
    echo "PORT must be a positive integer." >&2
    exit 1
    ;;
esac

exec uvicorn app.main:app --host "$host" --port "$port"
