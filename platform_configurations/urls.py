from rest_framework.routers import DefaultRouter
from platform_configurations.views import SytemStatusViewSet


router = DefaultRouter()

router.register("system-status", SytemStatusViewSet, basename="system-status")
