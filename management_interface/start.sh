#!/bin/sh

echo "Running Django Migrations"
python manage.py migrate \
&& python manage.py collectstatic --no-input \
&& python manage.py createsuperuser --noinput || true

echo "Starting Nginx"
service nginx start

echo "Starting Gunicorn"
gunicorn management_interface.wsgi:application --bind 0.0.0.0:8000 --timeout 120 --workers $GUNICORN_WORKERS --log-level $GUNICORN_LOGLEVEL --access-logfile - --error-logfile -