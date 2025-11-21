#!/bin/bash
set -e

# Get port from environment variable, default to 9000
PORT=${PORT:-9000}

echo "Starting Gunicorn on port $PORT..."

# Start gunicorn with dynamic port
exec gunicorn \
    --bind "0.0.0.0:$PORT" \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
