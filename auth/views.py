from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client


from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.views import PasswordChangeView

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status

from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from django_base.base_utils.utils import (
    get_random_string,
    email_template_sender,
    get_default_for_email_template,
)
from django_base.base_utils.base_viewsets import BaseGenericViewSet
from users.models import User, TokenRecovery


class PasswordRecoveryViewSet(BaseGenericViewSet):
    queryset = User.objects.all()
    permissions = {
        "default": [AllowAny],
    }

    def get_validated_token(self, email, token):
        token_recovery = TokenRecovery.objects.get(user__email=email, token=token)
        if (
            token_recovery.created_at + settings.PASSWORD_RECOVERY_TOKEN_EXPIRE_AT
            < timezone.now()
        ):
            raise ValidationError(_("Token expired"))
        return token_recovery

    def get_user(self, email):
        user = User.objects.get(email=email)
        return user

    @action(
        detail=False,
        methods=["post"],
        url_path="",
        url_name="password_recovery_email_send",
    )
    def recovery_send_mail(self, request):
        request_type = (
            request.data.get("request_type", "reset")
            if settings.PASSWORD_CHANGE_BY_EMAIL
            else "reset"
        )

        try:
            user = self.get_user(request.data.get("email"))

            recovery_token = get_random_string(settings.PASSWORD_RECOVERY_TOKEN_LENGTH)

            if TokenRecovery.objects.filter(user=user).exists():
                token_recovery = TokenRecovery.objects.get(user=user)
                token_recovery.delete()

            TokenRecovery.objects.create(user=user, token=recovery_token)

            url = (
                "/cambiar-contrasena/confirmar/"
                if request_type == "change"
                else "/recuperar-contrasena/confirmar/"
            )
            full_url = f"{settings.FRONT_URL}/{url}/{recovery_token}/{user.email}/"

            normalized_request_type = (
                "cambio" if request_type == "change" else "reseteo"
            )

            email_subject = f"Mail {normalized_request_type} de contraseña"

            context = {
                "password_recovery_token_type": settings.PASSWORD_RECOVERY_TOKEN_TYPE,
                "normalized_request_type": normalized_request_type,
                "recovery_token": recovery_token,
                "front_url": settings.FRONT_URL,
                "request_type": request_type,
                "full_url": full_url,
                "user": user,
            }
            context.update(get_default_for_email_template())

            email_template_sender(
                email_subject,
                "registration/password_recovery_email.html",
                context,
                user.email,
            )
        except Exception as e:
            print(e)
            pass

        return Response(_("Email sent"), status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="check-token",
        url_name="password_recovery_check_token",
    )
    def recovery_check_token(self, request):
        try:
            self.get_validated_token(
                request.data.get("email"), request.data.get("token")
            )
        except ValidationError as e:
            return Response(str(e.message), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(_("Token is invalid"), status=status.HTTP_400_BAD_REQUEST)

        return Response(_("Token is valid"), status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="confirm",
        url_name="password_recovery_confirm",
    )
    def recovery_confirm(self, request):
        try:
            password = request.data.get("password", "")
            user = self.get_user(request.data.get("email"))
            token_recovery = self.get_validated_token(
                request.data.get("email"), request.data.get("token")
            )
            validate_password(password, user=user)
        except ValidationError as e:
            if hasattr(e, "message"):
                return Response(str(e.message), status=status.HTTP_400_BAD_REQUEST)
            return Response(e, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(_("Token is invalid"), status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        token_recovery.delete()
        return Response(_("Password reset successful"), status=status.HTTP_200_OK)


class PasswordChangeViewModify(PasswordChangeView):
    def post(self, request, *args, **kwargs):
        if not settings.PASSWORD_CHANGE_BY_EMAIL:
            return Response(
                _("Only password change by email is allowed"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not "old_password" in request.data:
            return Response(
                _("old_password is required"), status=status.HTTP_400_BAD_REQUEST
            )
        old_password = request.data["old_password"]
        if not request.user.check_password(old_password):
            return Response(
                _("Old password is incorrect"), status=status.HTTP_400_BAD_REQUEST
            )
        if old_password == request.data["new_password"]:
            return Response(
                _("New password must be different from old password"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = request.data.copy()
        data["new_password1"] = data["new_password"]
        data["new_password2"] = data["new_password"]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # TODO Add is register complete permission??
        # request.user.is_register_completed = True
        # request.user.save()

        return Response(_("New password has been saved."), status=status.HTTP_200_OK)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.GOOGLE_REDIRECT_URI
