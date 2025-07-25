from datetime import timedelta
from django_base.settings.django_settings import BASE_APPS, AUTH_PASSWORD_VALIDATORS
from django_base.settings.environment_variables import (
    BROKER_SERVER,
    BROKER_SERVER_PORT,
    EMAIL_PROVIDER,
    CORS_ALLOWED_URLS,
    BASE_DIR,
    USE_S3,
    AWS_STORAGE_BUCKET_NAME,
    IS_PRODUCTION,
    SENTRY_DSN,
)
from django_base.settings.configurations import (
    USE_DEBUG_TOOLBAR,
    USE_CELERY,
    USE_WEB_SOCKET,
)


THIRD_APPS = [
    # "django_crontab",
]

if USE_WEB_SOCKET:
    # Load daphne and channels first
    THIRD_APPS = ["daphne", "channels"] + THIRD_APPS

MY_APPS = [
    "users",
    "django_global_places",
    "platform_configurations",
    "notifications",
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
ACCOUNT_EMAIL_SUBJECT_PREFIX = "\u200B"
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
    raise Exception("EMAIL_PROVIDER not allowed")

# <---------------------- Cors configurations ---------------------->
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_URLS
CORS_ORIGIN_WHITELIST = CORS_ALLOWED_URLS

# <---------------------- django-debug-toolbar configurations ---------------------->
# INTERNAL_IPS = [
#     "127.0.0.1",
#     "0.0.0.0"
# ]


if USE_DEBUG_TOOLBAR:
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "0.0.0.0"]


# <-------------- Celery configurations -------------->
if USE_CELERY:
    CELERY_BROKER = f"redis://:@{BROKER_SERVER}:{BROKER_SERVER_PORT}/0"
    CELERY_BROKER_URL = CELERY_BROKER
    CELERY_RESULT_BACKEND = CELERY_BROKER

# <-------------- Socket configurations -------------->
if USE_WEB_SOCKET:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(BROKER_SERVER, BROKER_SERVER_PORT)],
            },
        },
    }


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
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SITE_ID = 1

# <-------------- SWAGGER configurations -------------->
SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SHOW_REQUEST_HEADERS": True,
    "SECURITY_DEFINITIONS": {
        "api_key": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Write 'Token' in the field, followed by a space and then your token",
        }
    },
}


# <-------------- Sentry -------------->
if IS_PRODUCTION:
    import sentry_sdk

    if not SENTRY_DSN:
        raise Exception("SENTRY_DSN not found in environment variables")

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )


# <-------------- Google settings -------------->
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email", "openid"],
        "AUTH_PARAMS": {"access_type": "offline"},  # refresh_token
    }
}
