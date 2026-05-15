from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

from django_base.settings.configurations import (
    USE_DEBUG_TOOLBAR,
)
from django_base.settings.django_settings import AUTH_PASSWORD_VALIDATORS, BASE_APPS, MIDDLEWARE
from django_base.settings.environment_variables import (
    AWS_STORAGE_BUCKET_NAME,
    BASE_DIR,
    CORS_ALLOWED_URLS,
    EMAIL_PROVIDER,
    IS_PRODUCTION,
    SENTRY_DSN,
    USE_S3,
)

THIRD_APPS = []

MY_APPS = [
    "users",
    "platform_configurations",
]

INSTALLED_APPS = THIRD_APPS + MY_APPS + BASE_APPS

ASGI_APPLICATION = "django_base.asgi.application"

# <-------------- Media and Static settings --------- ----->
if USE_S3:
    # aws settings
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
    AWS_DEFAULT_ACL = None
    # s3 public media settings
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"

    STORAGES = {
        "default": {
            "BACKEND": "django_base.storage_backends.PublicMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"


# <---------------------- Auth configurations ---------------------->

# Allauth configurations
ACCOUNT_SIGNUP_FIELDS = ("email*", "password1*", "is_test_user")
ACCOUNT_ADAPTER = "users.adapter.CustomAccountAdapter"
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = "\u200b"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_UNIQUE_EMAIL = True

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

AUTH_USER_MODEL = "users.User"

REST_AUTH = {
    "USER_DETAILS_SERIALIZER": "users.serializers.UserSerializer",
    "REGISTER_SERIALIZER": "users.serializers.CustomRegisterSerializer",
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_RETURN_EXPIRATION": True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=5),
}


# <---------------------- Email configurations ---------------------->
if EMAIL_PROVIDER == "console":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
elif EMAIL_PROVIDER == "aws":
    EMAIL_BACKEND = "django_ses.SESBackend"
elif EMAIL_PROVIDER == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    raise ImproperlyConfigured(f"EMAIL_PROVIDER '{EMAIL_PROVIDER}' not allowed")

# <---------------------- Cors configurations ---------------------->
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_URLS

# <---------------------- django-debug-toolbar configurations ---------------------->
if USE_DEBUG_TOOLBAR:
    import socket

    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
    MIDDLEWARE = MIDDLEWARE + ["debug_toolbar.middleware.DebugToolbarMiddleware"]

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "0.0.0.0"]


CUSTOM_AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django_base.base_utils.base_validators.UpperValidator",
    },
    {
        "NAME": "django_base.base_utils.base_validators.SymbolValidator",
    },
]

for validator in CUSTOM_AUTH_PASSWORD_VALIDATORS:
    if validator not in AUTH_PASSWORD_VALIDATORS:
        AUTH_PASSWORD_VALIDATORS.append(validator)

# <---------------------- Rest configurations ---------------------->
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "dj_rest_auth.jwt_auth.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "django_base.base_utils.base_pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "password_recovery": "5/hour",
    },
}

SITE_ID = 1

# <-------------- drf-spectacular configurations -------------->
SPECTACULAR_SETTINGS = {
    "TITLE": "Base project API",
    "DESCRIPTION": "Base project documentation",
    "VERSION": "1.0.0",
    "CONTACT": {"email": "contact@linkchar.com"},
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
}


# <-------------- Sentry -------------->
if IS_PRODUCTION:
    import logging as _logging

    if not SENTRY_DSN:
        _logging.getLogger(__name__).warning(
            "SENTRY_DSN not set in production — error tracking disabled"
        )
    else:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
