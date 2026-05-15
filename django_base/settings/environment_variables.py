import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# <--------------- General configurations -------------->
DEBUG = env.bool("DEBUG", default=True)
IS_PRODUCTION = env.bool("IS_PRODUCTION", default=False)
SECRET_KEY = (
    env("SECRET_KEY") if IS_PRODUCTION else env("SECRET_KEY", default="dev-insecure-secret-key")
)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")


# <-------------- urls settings -------------->
FRONT_URL = env("FRONT_URL", default="http://localhost:3000")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[]) if not DEBUG else ["*"]
CORS_ALLOWED_URLS = env.list("CORS_ALLOWED_URLS", default=[]) + [FRONT_URL]


# <-------------- DB settings -------------->
DB_ENGINE = env("DB_ENGINE", default="sqlite3")
DB_USER = env("DB_USER", default="")
DB_PASSWORD = env("DB_PASSWORD", default="")
DB_HOST = env("DB_HOST", default="")
DB_PORT = env("DB_PORT", default="")
DB_NAME = env("DB_NAME", default="")


# <-------------- Email env settings -------------->
EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="console")

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="project@linkchar.com")


# <-------------- S3 -------------->
USE_S3 = env.bool("USE_S3", default=False)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")


# <-------------- Sentry settings -------------->
SENTRY_DSN = env("SENTRY_DSN", default="")
