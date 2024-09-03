#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.5
done

echo "PostgreSQL started"

python manage.py makemigrations
python manage.py migrate --no-input
daphne -b 0.0.0.0 -p 8000 djbackend.asgi:application