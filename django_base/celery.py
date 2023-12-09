from celery import Celery
import os

# establecer el valor predeterminado de Django settings module para tu proyecto.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_base.settings')

app = Celery('django_base')

# Usar la configuración de Django para la configuración de Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas automatizadas
app.autodiscover_tasks()