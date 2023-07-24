import os

import hashlib

import datetime

from django.contrib.auth.models import UserManager
from django.db import models

from django_base.utils import get_date_with_timezone
from django.utils import timezone


class BaseCustomManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


class BaseUserCustomManager(BaseCustomManager, UserManager):
    pass


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseSoftDeleteModel(BaseModel):
    objects = BaseCustomManager()
    unfiltered_objects = models.Manager()

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.deleted_at = timezone.now()
        self.save()


class CustomFileField(models.FileField):
    def generate_filename(self, instance, filename):
        extension = filename.split(".")[-1]
        filename = "{}.{}".format(
            hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest(), extension
        )
        return os.path.join(self.upload_to, filename)


class CustomImageField(models.ImageField):
    def generate_filename(self, instance, filename):
        extension = filename.split(".")[-1]
        filename = "{}.{}".format(
            hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest(), extension
        )
        return os.path.join(self.upload_to, filename)
