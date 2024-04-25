from django_base.settings.django_settings import BASE_DIR
from django_base.settings.environment_variables import (
    DB_ENGINE, DB_HOST, DB_NAME,
    DB_PASSWORD, DB_PORT, DB_USER
)

# <-------------- DB settings -------------->
ALLOWED_DB_ENGINES = {
    "sqlite3": "django.db.backends.sqlite3",
    "mysql": "django.db.backends.mysql",
    "postgresql": "django.db.backends.postgresql",
    "oracle": "django.db.backends.oracle",
}

if DB_ENGINE not in ALLOWED_DB_ENGINES.keys():
    raise Exception("DB_ENGINE not allowed")

if DB_ENGINE == "sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": ALLOWED_DB_ENGINES[DB_ENGINE],
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

elif DB_ENGINE == "oracle":
    DATABASES = {
        "default": {
            "ENGINE": ALLOWED_DB_ENGINES[DB_ENGINE],
            "NAME": f"{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
        }
    }

else:
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
