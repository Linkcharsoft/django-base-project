from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from allauth.account.views import ConfirmEmailView

from dj_rest_auth.registration.serializers import VerifyEmailSerializer
from dj_rest_auth.views import PasswordChangeView

from django_base.settings import BACK_URL, EMAIL_HOST_USER, APP_NAME
from django.utils.translation import gettext_lazy as _

from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from datetime import timedelta
from django.utils import timezone


from users.models import User, TokenRecovery
from users.utils import get_random_string


class EmailVerification(APIView, ConfirmEmailView):
    def get(self, request, key):
        return render(
            request,
            "registration/verify_email.html",
            context={"key": key, "BASE_URL": BACK_URL},
        )

    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.kwargs["key"] = serializer.validated_data["key"]
        confirmation = self.get_object()
        confirmation.confirm(self.request)
        return Response("ok", status=status.HTTP_200_OK)


class Password_recovery_email_send(APIView):
    def post(self, request):
        try:
            recovery_token = get_random_string(6)
            email = request.data["email"]

            user = get_object_or_404(User, email=email)
            if TokenRecovery.objects.filter(user=user).exists():
                token_recovery = TokenRecovery.objects.get(user=user)
                token_recovery.delete()
            TokenRecovery.objects.create(user=user, token=recovery_token)

            email_plaintext_message = (
                "Hi,\n\n \
            You have requested a password reset for your account.\n \
            Please enter this code in "
                + APP_NAME
                + " app: "
                + recovery_token
                + "\n \
            If you did not request a password reset, please ignore this email.\n\n \
            Thank you,\n "
                + APP_NAME
                + " Team"
            )
            send_mail(
                # title:
                "Password Reset for {title}".format(title=APP_NAME),
                # message:
                email_plaintext_message,
                # from:
                EMAIL_HOST_USER,
                # to:
                [email],
            )
            return Response("Email sent", status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                f"Something went wrong {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class Check_token(APIView):
    def post(self, request):
        try:
            token = request.data["token"]
            email = request.data["email"]
            user = get_object_or_404(User, email=email)
            if TokenRecovery.objects.filter(user=user).exists():
                token_recovery = TokenRecovery.objects.get(user=user)
                if token_recovery.token == token:
                    if (
                        token_recovery.created_at + timedelta(minutes=10)
                        < timezone.now()
                    ):
                        return Response(
                            "Token expired", status=status.HTTP_400_BAD_REQUEST
                        )
                    else:
                        return Response("Token is valid", status=status.HTTP_200_OK)
                else:
                    return Response(
                        "Token is invalid", status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    "This user has no token request", status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                f"Something went wrong.{str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class Password_recovery_confirm(APIView):
    def post(self, request):
        try:
            token = request.data["token"]
            email = request.data["email"]
            password = request.data["password"]
            user = get_object_or_404(User, email=email)
            if TokenRecovery.objects.filter(user=user).exists():
                token_recovery = TokenRecovery.objects.get(user=user)
                if token_recovery.token == token:
                    if (
                        token_recovery.created_at + timedelta(minutes=10)
                        < timezone.now()
                    ):
                        return Response(
                            "Token expired", status=status.HTTP_400_BAD_REQUEST
                        )

                    else:
                        try:
                            validate_password(password, user=user)
                        except ValidationError as e:
                            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

                        user.set_password(password)
                        user.save()
                        token_recovery.delete()
                        return Response(
                            "Password reset successful", status=status.HTTP_200_OK
                        )
                else:
                    return Response(
                        "Token is invalid", status=status.HTTP_400_BAD_REQUEST
                    )

            else:
                return Response(
                    "This user has no token request", status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                f"Something went wrong. {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PasswordChangeViewModify(PasswordChangeView):
    def post(self, request, *args, **kwargs):
        if not "old_password" in request.data:
            return Response(
                "old_password is required", status=status.HTTP_400_BAD_REQUEST
            )
        old_password = request.data["old_password"]
        if not request.user.check_password(old_password):
            return Response(
                "Old password is incorrect", status=status.HTTP_400_BAD_REQUEST
            )
        if old_password == request.data["new_password1"]:
            return Response(
                "New password must be different from old password",
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.is_register_completed = True
        request.user.save()
        return Response("New password has been saved.", status=status.HTTP_200_OK)
