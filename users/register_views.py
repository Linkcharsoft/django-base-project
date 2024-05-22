from datetime import timedelta

from allauth.account.views import ConfirmEmailView

from dj_rest_auth.registration.serializers import VerifyEmailSerializer
from dj_rest_auth.views import PasswordChangeView

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from users.models import User, TokenRecovery
from django_base.base_utils.utils import get_random_string, email_template_sender


def _get_validated_token(request):
    token_recovery = TokenRecovery.objects.get(
        user__email=request.data.get("email"), token=request.data.get("token")
    )
    if token_recovery.created_at + timedelta(minutes=30) < timezone.now():
        raise ValidationError(_("Token expired"))
    return token_recovery


def _get_user(email):
    user = User.objects.get(email=email)
    return user


@method_decorator(csrf_exempt, name="dispatch")
class EmailVerification(APIView, ConfirmEmailView):
    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.kwargs["key"] = serializer.validated_data["key"]
        confirmation = self.get_object()
        confirmation.confirm(self.request)
        return Response("ok", status=status.HTTP_200_OK)


# <------------------ Password recovery ------------------>
class Password_recovery_email_send(APIView):
    def post(self, request):
        request_type = (
            request.data.get("request_type", "reset")
            if settings.PASSWORD_CHANGE_BY_EMAIL
            else "reset"
        )

        try:
            user = _get_user(request.data.get("email"))

            token_length = 25 if settings.PASSWORD_EMAIL_SEND == "link" else 6
            recovery_token = get_random_string(token_length)

            if TokenRecovery.objects.filter(user=user).exists():
                token_recovery = TokenRecovery.objects.get(user=user)
                token_recovery.delete()
            TokenRecovery.objects.create(user=user, token=recovery_token)


            email_subject = f"Password Reset for {settings.APP_NAME}"

            context = {
                "FRONT_URL": settings.FRONT_URL,
                "recovery_token": recovery_token,
                "APP_NAME": settings.APP_NAME,
                "REQUEST_TYPE": request_type,
                "PASSWORD_EMAIL_SEND": settings.PASSWORD_EMAIL_SEND,
                "EMAIL": user.email,
            }

            email_template_sender(
                email_subject,
                "registration/password_recovery_email.html",
                context,
                user.email,
            )
        except Exception:
            pass
        return Response(_("Email sent"), status=status.HTTP_200_OK)



class Check_token(APIView):
    def post(self, request):
        try:
            _get_validated_token(request)
        except ValidationError as e:
            return Response(str(e.message), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(_("Token is invalid"), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(_("Token is valid"), status=status.HTTP_200_OK)


class Password_recovery_confirm(APIView):
    def post(self, request):
        try:
            password = request.data.get("password", "")
            user = _get_user(request.data.get("email"))
            token_recovery = _get_validated_token(request)
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
        return Response("Password reset successful", status=status.HTTP_200_OK)


# / <------------------ Password recovery ------------------>


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
        request.user.is_register_completed = True
        request.user.save()
        return Response("New password has been saved.", status=status.HTTP_200_OK)
            
