#!/bin/sh
set -e

# 1. Читаем пароль из Docker secret, если он есть
if [ -f /run/secrets/postgres_password ]; then
  POSTGRES_PASSWORD="$(cat /run/secrets/postgres_password | tr -d '\r\n')"
else
  # Фоллбек — если вдруг запустили без secret (например, локально)
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
fi

# 2. Собираем DSN для приложения
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

export POSTGRES_DSN="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

echo "Using POSTGRES_DSN=${POSTGRES_DSN}"

# 3. Передаём управление основному процессу (из CMD Dockerfile)
exec "$@"
