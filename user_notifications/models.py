from django.db import models
from notifications.signals import notify
from user_notifications.expo_utils import expo_push_notification_handler
from django.conf import settings


if settings.USE_EXPO_NOTIFICATIONS:
    class ExpoToken(models.Model):
        token = models.CharField(max_length=200)
        user = models.ForeignKey(
            "users.User", on_delete=models.CASCADE, related_name="expo_tokens"
        )
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"{self.user} - {self.token}"


    notify.connect(
        expo_push_notification_handler, dispatch_uid="expo_push_notification_handler"
    )
