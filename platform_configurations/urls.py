from rest_framework.routers import DefaultRouter

from platform_configurations.views import SystemStatusViewSet

router = DefaultRouter()

router.register("system-status", SystemStatusViewSet, basename="system-status")
