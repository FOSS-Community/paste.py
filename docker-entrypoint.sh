#!/bin/sh
set -e

# Run migrations
pdm run migrate

# Execute the main command
exec "$@"