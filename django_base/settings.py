from email.policy import default
from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# <-------------- General env settings -------------->
SECRET_KEY = env("SECRET_KEY", default = '-----------')
DEBUG = env.bool("DEBUG", default=True)
BACK_URL = env("BACK_URL", default="http://localhost:8000")
FRONT_URL = env("FRONT_URL", default="http://localhost:3000")
APP_NAME = env("APP_NAME", default="Django Base")

# <-------------- DB env settings -------------->
DB_ENGINE = env("DB_ENGINE", default="sqlite3")
DB_USER = env("DB_USER", default="")
DB_PASSWORD = env("DB_PASSWORD", default="")
DB_HOST = env("DB_HOST", default="")
DB_PORT = env("DB_PORT", default="")
DB_NAME = env("DB_NAME", default="")

# <-------------- Auth env settings -------------->
USE_EMAIL_FOR_AUTHENTICATION = env.bool("USE_EMAIL_FOR_AUTHENTICATION", default=False)

# <-------------- Email env settings -------------->
EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="console")

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env("EMAIL_PORT", default=587)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SES_AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
SES_AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")

# <-------------- CORS env settings -------------->
CORS_ALLOWED_URLS = env.list("CORS_ALLOWED_URLS", default=[])

# <-------------- Watchman env settings -------------->
WATCHMAN_TOKEN = env("WATCHMAN_TOKEN", default="password")

# <-------------- S3 env -------------->
USE_S3 = env.bool("USE_S3", default=True)

# aws settings
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_LOCATION = "static"
AWS_DEFAULT_ACL = None
# s3 static settings
STATICFILES_STORAGE = "django_base.storage_backends.StaticStorage"
# s3 public media settings
DEFAULT_FILE_STORAGE = "django_base.storage_backends.PublicMediaStorage"
# s3 private media settings
PRIVATE_MEDIA_LOCATION = "private"
PRIVATE_FILE_STORAGE = "django_base.storage_backends.PrivateMediaStorage"


# <-------------- General settings -------------->
if not DEBUG:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
else:
    ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# <-------------- Apps settings -------------->
BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.twitter",
    "drf_yasg",
    "corsheaders",
    "debug_toolbar",
    "django_extensions",
    "watchman",
    "django_filters",
]

MY_APPS = [
    "users",
]

INSTALLED_APPS = BASE_APPS + THIRD_APPS + MY_APPS


# <-------------- Django base settings -------------->
MIDDLEWARE = [
    "django_base.middlewares.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "django_base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "django_base.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "django_base.validators.UpperValidator",
    },
    {
        "NAME": "django_base.validators.SymbolValidator",
    },
    {
        "NAME": "django_base.validators.NumberRequiredValidator",
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# <-------------- DB settings -------------->
if DB_ENGINE == "sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    ALLOWED_DB_ENGINES = {
        "mysql": "django.db.backends.mysql",
        "postgresql": "django.db.backends.postgresql",
    }
    if DB_ENGINE not in ALLOWED_DB_ENGINES.keys():
        raise Exception("DB_ENGINE not allowed")

    DATABASES = {
        "default": {
            "ENGINE": ALLOWED_DB_ENGINES[DB_ENGINE],
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }

# <-------------- Lenguaje and timezone settings -------------->
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# <-------------- Media and Static settings -------------->
if USE_S3:
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    STATIC_LOCATION = "static"                                        #If no apache is used, remove this line and add whitenose
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/" #If no apache is used, remove this line and add whitenose


else:
    STATIC_URL = "/static/" #If no apache is used, move this line out of the else
    STATIC_ROOT = BASE_DIR / "static" #If no apache is used, move this line out of the else

    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# <---------------------- Email configurations ---------------------->
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# <---------------------- Rest configurations ---------------------->
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "django_base.pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "PAGE_SIZE": 10,
}

SITE_ID = 1

# <---------------------- Auth configurations ---------------------->
if USE_EMAIL_FOR_AUTHENTICATION:
    ACCOUNT_EMAIL_REQUIRED = True
    ACOOUNT_UNIQUE_EMAIL = True

    ACCOUNT_EMAIL_VERIFICATION = "mandatory"
    ACCOUNT_AUTHENTICATION_METHOD = "email"

    ACCOUNT_USERNAME_REQUIRED = False

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

AUTH_USER_MODEL = "users.User"

REST_AUTH = {
    "USER_DETAILS_SERIALIZER": "users.serializers.UserSerializer",
}

# <---------------------- Email configurations ---------------------->
if EMAIL_PROVIDER == "console":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
elif EMAIL_PROVIDER == "aws":
    EMAIL_BACKEND = "django_ses.SESBackend"
elif EMAIL_PROVIDER == "smpt":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    raise Exception("EMAIL_PROVIDER not allowed")

# <---------------------- Cors configurations ---------------------->
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_URLS

CORS_ORIGIN_WHITELIST = CORS_ALLOWED_URLS

# <---------------------- django-debug-toolbar configurations ---------------------->
INTERNAL_IPS = [
    "127.0.0.1",
]
