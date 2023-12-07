from django.utils import timezone

from django_base import settings
from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        activate_url = (
            settings.FRONT_URL + f"/registro/validar-email/{emailconfirmation.key}/"
        )

        return activate_url
