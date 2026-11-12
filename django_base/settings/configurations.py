from datetime import timedelta

from django_base.settings.environment_variables import BASE_DIR

# <-------------- General configurations -------------->
APP_NAME = "Django Base"
USE_DEBUG_TOOLBAR = False
BASE_EMAILS_BANNER_URL = "https://linkchar-static-bk.s3.us-east-1.amazonaws.com/Linkchar-banner.jpg"
# Shown in the mail footer so recipients have somewhere to reply. Empty omits the line.
BASE_EMAILS_CONTACT_EMAIL = ""

# <-------------- Auth configurations -------------->
PASSWORD_CHANGE_BY_EMAIL = True

PASSWORD_RECOVERY_TOKEN_TYPE = "link"  # link | code
PASSWORD_RECOVERY_TOKEN_EXPIRE_AT = timedelta(minutes=30)
PASSWORD_RECOVERY_TOKEN_LENGTH = 25 if PASSWORD_RECOVERY_TOKEN_TYPE == "link" else 6

# <-------------- Sessions and login attempts (security app) -------------->
# A session (JWT pair) dies after SESSION_IDLE_TTL without use, and never outlives SESSION_MAX_TTL.
SESSION_IDLE_TTL = timedelta(days=3)
SESSION_MAX_TTL = timedelta(days=7)

# Login attempts allowed per window, counted on LoginEvent (shared by the API and the admin login).
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=1)
LOGIN_RATE_LIMIT_PER_IP = 30
LOGIN_RATE_LIMIT_PER_EMAIL = 10

# Admin alert: a user with this many failed logins inside the window is flagged.
SECURITY_FAILED_LOGINS_WINDOW = timedelta(days=7)
SECURITY_FAILED_LOGINS_ALERT = 5

# `purge_security_records`: login events older than this, and sessions that ended this long ago.
LOGIN_EVENT_RETENTION = timedelta(days=90)
AUTH_SESSION_RETENTION = timedelta(days=30)

# <-------------- Lenguaje and timezone settings -------------->
LOCALE_PATHS = [
    f"{BASE_DIR}/locale",
]

LANGUAGES = [
    ("en", "English"),
]
