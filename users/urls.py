from rest_framework.routers import DefaultRouter

from django.urls import path

from users.views import UserViewSet
from users.register_views import (
    Password_recovery_email_send,
    Check_token,
    Password_recovery_confirm,
    PasswordChangeViewModify,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")

# fmt: off
urlpatterns = [
    path('password-change/', PasswordChangeViewModify.as_view(), name='rest_password_change'),
    path('password-recovery/', Password_recovery_email_send.as_view(), name='password_recovery_email_send'),
    path('password-recovery/check-token/', Check_token.as_view(), name='check_token'),
    path('password-recovery/confirm/', Password_recovery_confirm.as_view(), name='password_recovery_confirm'),
]
# fmt: on
