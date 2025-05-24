#!/bin/sh
# entrypoint.sh

echo "Running database migrations..."
flask db upgrade

echo "Starting Flask application..."
# Defer to the command provided, e.g., gunicorn command from docker-compose.yml
exec "$@"