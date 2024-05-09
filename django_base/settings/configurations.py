from django_base.settings.environment_variables import BASE_DIR


# <-------------- General configurations -------------->
APP_NAME = "Django Base"
USE_DEBUG_TOOLBAR = False

# <-------------- Auth configurations -------------->
USE_EMAIL_FOR_AUTHENTICATION = True
PASSWORD_EMAIL_SEND = "link" #link/code
PASSWORD_CHANGE_BY_EMAIL = False
USE_JWT = False

# <-------------- Lenguaje and timezone settings -------------->
LOCALE_PATHS = [
    f"{BASE_DIR}/locale",
    ]

LANGUAGES = [
        ("en", "English"),
        ("es", "Spanish"),
    ]


# <-------------- Global places env settings -------------->
GLOBAL_PLACES = {
    "INCLUDE_LOCATION": False,
    "LOCATION_SCOPE": "state",
    "INCLUDE_EXPANDED_COUNTRY": False,
}


# <-------------- Async settings --------------> #tmp until cookiecutter update
USE_CELERY=False
USE_WEB_SOCKET=False

