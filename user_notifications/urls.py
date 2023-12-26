from rest_framework.routers import DefaultRouter
from user_notifications.views import NotificationsViewSet


router = DefaultRouter()
router.register(r"user-notifications", NotificationsViewSet, basename="notifications")


# fmt: off
urlpatterns = [

]
# fmt: on