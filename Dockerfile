FROM python:3.12.3

RUN apt update

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update && apt-get install -y cron

RUN apt-get install gettext -y

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x ./entrypoint.sh

# Run the Python code to generate the cron file
RUN python manage.py shell -c "from django_notifications_views.cron_config import write_cron_job; write_cron_job()"

# Verifica que el archivo cron se haya generado en la ubicación correcta
RUN ls /code

# Add the generated crontab file
RUN crontab /code/notifications_cron

# Comando por defecto para iniciar el cron y el servidor Django
CMD ["sh", "-c", "service cron start && python manage.py runserver 0.0.0.0:8000"]
