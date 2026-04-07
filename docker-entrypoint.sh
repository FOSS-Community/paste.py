#!/bin/sh
set -e

echo "Running database migrations..."
pdm run migrate

echo "Starting application..."
exec "$@"
