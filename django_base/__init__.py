from __future__ import absolute_import, unicode_literals

# Esto asegurará que la aplicación siempre se importe cuando
# Django inicie para que se puedan usar las tareas compartidas.
from django_base.celery import app as celery_app

__all__ = ('celery_app',)
