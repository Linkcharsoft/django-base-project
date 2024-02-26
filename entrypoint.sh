#!/bin/bash

python manage.py migrate

python manage.py collectstatic --noinput

gunicorn -w 3 -b :8000 django_base.wsgi:application
# daphne -b 0.0.0.0 -p 8000 django_base.asgi:application