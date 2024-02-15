#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.5
done

echo "PostgreSQL started"

python manage.py migrate --no-input

exec "$@"