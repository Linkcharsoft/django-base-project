from allauth.account.models import EmailAddress

from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.db.models import UniqueConstraint
from django.dispatch import receiver
from django.db import models

from django_base.base_utils.base_models import (
    BaseSoftDeleteModel,
    BaseUserCustomManager,
)


class User(BaseSoftDeleteModel, AbstractUser):
    objects = BaseUserCustomManager()

    class Meta:
        constraints = [
            UniqueConstraint(
                name="unique_username",
                fields=["username"],
                condition=models.Q(deleted=False),
            ),
            UniqueConstraint(
                name="unique_email",
                fields=["email"],
                condition=models.Q(deleted=False),
            ),
        ]


class Profile(BaseSoftDeleteModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_register_complete = models.BooleanField(default=False)

    def complete_register(self):
        self.is_register_complete = True
        self.save()


class TokenRecovery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=25, default="")
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=User)
def create_profile(sender, instance, **kwargs):
    if kwargs["created"]:
        Profile.objects.create(user=instance)
        if instance.is_superuser:
            EmailAddress.objects.create(
                user=instance, email=instance.email, verified=True, primary=True
            )
    else:
        instance.profile.deleted = instance.deleted
        instance.profile.save()
