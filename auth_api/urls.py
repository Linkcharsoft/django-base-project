from dj_rest_auth.views import UserDetailsView
from django.urls import include, path

from auth_api.views import PasswordChangeViewModify, PasswordRecoveryViewSet
from security.views import (
    LoginView,
    LogoutAllView,
    LogoutView,
    SessionRefreshView,
    SessionTokenVerifyView,
    SessionViewSet,
)

recovery_send_mail = PasswordRecoveryViewSet.as_view({"post": "recovery_send_mail"})
recovery_check_token = PasswordRecoveryViewSet.as_view({"post": "recovery_check_token"})
recovery_confirm = PasswordRecoveryViewSet.as_view({"post": "recovery_confirm"})
session_list = SessionViewSet.as_view({"get": "list"})
session_detail = SessionViewSet.as_view({"delete": "destroy"})


# fmt: off
urlpatterns = [
    # dj_rest_auth login/logout/refresh, backed by revocable sessions (security app)
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),

    # JWT
    path("token/verify/", SessionTokenVerifyView.as_view(), name="rest_token_verify"),
    path("token/refresh/", SessionRefreshView.as_view(), name="rest_token_refresh"),

    # The user's own sessions
    path("sessions/", session_list, name="auth_session_list"),
    path("sessions/<uuid:pk>/", session_detail, name="auth_session_detail"),
    path("logout-all/", LogoutAllView.as_view(), name="rest_logout_all"),

    # Password
    path("password/change/", PasswordChangeViewModify.as_view(), name="rest_password_change"),
    path("password/recovery/", recovery_send_mail, name="rest_password_recovery_email_send"),
    path("password/recovery/check-token/", recovery_check_token, name="rest_password_check_token"),
    path("password/recovery/confirm/", recovery_confirm, name="rest_password_recovery_confirm"),

    # Registration. allauth only needs the two named routes this include defines
    # (account_confirm_email, account_email_verification_sent); its own HTML views
    # (allauth.urls) are not mounted, so nobody logs in around the rate limit and LoginEvent.
    path("registration/", include("dj_rest_auth.registration.urls")),
]
# fmt: on
