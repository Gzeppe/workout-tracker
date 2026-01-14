web: cd web && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
release: cd web && python manage.py migrate && python manage.py load_exercises
