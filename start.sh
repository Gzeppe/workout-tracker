#!/bin/bash
set -e

echo "Running migrations..."
cd web && python manage.py migrate --noinput

echo "Loading exercises..."
python manage.py load_exercises

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
