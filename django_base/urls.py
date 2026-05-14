from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from platform_configurations.urls import router as platform_configurations_router
from users.urls import router as users_router

base_router = DefaultRouter()
base_router.registry.extend(users_router.registry)
base_router.registry.extend(platform_configurations_router.registry)


# fmt: off
#<-------------- Django + libraries urls -------------->
urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

# <-------------- API schema (drf-spectacular) -------------->
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

#<-------------- Our apps includes -------------->
urlpatterns += [
    path("api/auth/", include("auth.urls")),
]

#<-------------- Our base router -------------->
urlpatterns += [path("api/", include(base_router.urls)),]

# fmt: on
