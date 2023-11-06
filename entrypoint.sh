#!/bin/bash

python manage.py migrate

gunicorn -w 3 -b :8000 django_base.wsgi:application
