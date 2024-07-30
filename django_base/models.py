from django.db import models
from django.utils.translation import gettext_lazy as _


class SystemStatus(models.Model):
    is_operational = models.BooleanField(default=True, verbose_name=_("Is operational"))

    class Meta:
        app_label = "django_base"
        verbose_name = _("System Status")
        verbose_name_plural = _("System Status")

    @classmethod
    def get_status(cls):
        status, created = cls.objects.get_or_create(pk=1)
        return status
