#!/usr/bin/env sh
# Runs before the container's main command. Migrations are opt-in so that
# multiple replicas starting at once don't race (use a one-off job or a single
# replica with RUN_MIGRATIONS=true).
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
