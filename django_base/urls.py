from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from dj_rest_auth.registration.views import ResendEmailVerificationView, RegisterView

from rest_framework.routers import DefaultRouter

from django.contrib import admin
from django.urls import path, include, re_path

from users.urls import router as users_router
from django_global_places.urls import router as django_global_places_router
from user_notifications.urls import router as user_notifications_router
from users.register_views import EmailVerification


schema_view = get_schema_view(
    openapi.Info(
        title="Base project API",
        default_version="v1",
        description="Base project documentation",
        contact=openapi.Contact(email="contact@linkchar.com"),
    ),
    public=True,
)

base_router = DefaultRouter()
base_router.registry.extend(users_router.registry)
base_router.registry.extend(django_global_places_router.registry)
base_router.registry.extend(user_notifications_router.registry)

# fmt: off
#<-------------- Django + libraries urls -------------->
urlpatterns = [
    path('admin/', admin.site.urls),
    path('__debug__/', include('debug_toolbar.urls')),

]

#<-------------- Dj-rest-auth urls -------------->
urlpatterns += [
    path('api/auth/registration/account-email-verification-sent/', EmailVerification.as_view(), name='account_email_verification_sent'),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    path('api/auth/register/', RegisterView.as_view(), name='rest_register'),

    path('api/auth/registration/resend-email/', ResendEmailVerificationView.as_view(), name="rest_resend_email"),
    re_path("api/auth/registration/account-confirm-email/(?P<key>[\s\d\w().+-_',:&]+)/$", EmailVerification.as_view(), name='account_confirm_email'),

    path('api/allauth/', include('allauth.urls')),
]

# <-------------- Swagger urls -------------->
urlpatterns += [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

#<-------------- Our apps includes -------------->
urlpatterns += [
    path('api/users/', include('users.urls')),
]

#<-------------- Our base router -------------->
urlpatterns += [path('api/', include(base_router.urls)),]

#<-------------- Media urls -------------->
# Uncomment the following line to serve media files
# urlpatterns += [re_path(r"media/(?P<path>.*)", SignedMediaView.as_view(), name="signed-media")]

# fmt: on
