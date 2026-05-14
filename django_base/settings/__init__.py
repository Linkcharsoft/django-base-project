from split_settings.tools import include

_base_settings = (
    "environment_variables.py",
    "django_settings.py",
    "custom_settings.py",
    "db_settings.py",
    "configurations.py",
)

include(*_base_settings)
