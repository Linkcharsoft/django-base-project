from django.urls import path, include

from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from dj_rest_auth.jwt_auth import get_refresh_view

from rest_framework_simplejwt.views import TokenVerifyView

from auth.views import PasswordChangeViewModify, PasswordRecoveryViewSet, GoogleLogin


recovery_send_mail = PasswordRecoveryViewSet.as_view({"post": "recovery_send_mail"})
recovery_check_token = PasswordRecoveryViewSet.as_view({"post": "recovery_check_token"})
recovery_confirm = PasswordRecoveryViewSet.as_view({"post": "recovery_confirm"})


# fmt: off
urlpatterns = [
    # URLs from dj_rest_auth.urls
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),

    # JWT
    path("token/verify/", TokenVerifyView.as_view(), name="rest_token_verify"),
    path("token/refresh/", get_refresh_view().as_view(), name="rest_token_refresh"),
    
    # Password
    path("password/change/", PasswordChangeViewModify.as_view(), name="rest_password_change"),
    path("password/recovery/", recovery_send_mail, name="rest_password_recovery_email_send"),
    path("password/recovery/check-token/", recovery_check_token, name="rest_password_check_token"),
    path("password/recovery/confirm/", recovery_confirm, name="rest_password_recovery_confirm"),

    # Registration
    path("registration/", include("dj_rest_auth.registration.urls")),

    path("allauth/", include("allauth.urls")),

    path("dj-rest-auth/google/", GoogleLogin.as_view(), name="google_login"),
]
# fmt: on
