#!/bin/bash
set -e

python manage.py migrate

# python manage.py crontab add #If you have any crontab jobs

python manage.py runserver 0.0.0.0:8000
