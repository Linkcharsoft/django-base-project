#!/bin/bash

python manage.py migrate

python manage.py collectstatic --noinput

# Ejecutar el código para generar el archivo de cron
python manage.py shell -c "from django_notifications_views.cron_config import write_cron_job; write_cron_job()"

# Registrar el archivo de cron
crontab /django_base/notifications_cron

# Iniciar el servicio de cron
service cron start

gunicorn -w 3 -b :8000 django_base.wsgi:application
# daphne -b 0.0.0.0 -p 8000 django_base.asgi:application