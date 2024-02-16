#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.5
done

echo "PostgreSQL started"

python manage.py migrate --no-input
gunicorn djbackend.wsgi:application --bind 0.0.0.0:8000 --timeout 0 --workers=5