from allauth.account.adapter import DefaultAccountAdapter

from django.conf import settings

from django_base.base_utils.utils import get_default_for_email_template


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        activate_url = (
            settings.FRONT_URL + f"/registro/validar-email/{emailconfirmation.key}/"
        )

        return activate_url

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        ctx = {
            "user": emailconfirmation.email_address.user,
            "key": emailconfirmation.key,
            "activate_url": self.get_email_confirmation_url(request, emailconfirmation),
            "request": request,
        }
        ctx.update(get_default_for_email_template())

        email_template = "account/email/email_confirmation"
        self.send_mail(email_template, emailconfirmation.email_address.email, ctx)
