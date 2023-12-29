import os

import hashlib

import datetime

from django.contrib.auth.models import UserManager
from django.db import models

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
        if "hard_delete" in kwargs and kwargs["hard_delete"]:
            kwargs.pop("hard_delete")
            super().delete(*args, **kwargs)
        else:
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
        #md5 hash updated to sha256 (Not tested)
        filename = "{}.{}".format(
            hashlib.sha256(str(datetime.datetime.now()).encode()).hexdigest(), extension
        )
        return os.path.join(self.upload_to, filename)


#<-------------- Locations -------------->


class AbstactCountry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    iso3 = models.CharField(max_length=3)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class AbstactExpandedCountry(AbstactCountry):
    iso2 = models.CharField(max_length=2, null=True, blank=True)
    numeric_code = models.CharField(max_length=3, null=True, blank=True)
    phone_code = models.CharField(max_length=3, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    currency_name = models.CharField(max_length=100, null=True, blank=True)
    currency_symbol = models.CharField(max_length=3, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class AbstractState(models.Model):
    json_id = models.IntegerField()
    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=5)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    country = models.ForeignKey('platform_configurations.Country', on_delete=models.CASCADE, related_name='states')
    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class AbstractCity(models.Model):
    json_id = models.IntegerField()
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)

    state = models.ForeignKey('platform_configurations.State', on_delete=models.CASCADE, related_name='cities')

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

#<-------------- Locations -------------->
