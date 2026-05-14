import os
from pathlib import Path

import environ
from django.core.wsgi import get_wsgi_application

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


if env("IS_SERVER", default=True):
    import signal
    import sys
    import time
    import traceback

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_base.settings"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_base.settings")
    try:
        application = get_wsgi_application()
    except Exception:
        # Error loading applications
        if "mod_wsgi" in sys.modules:
            traceback.print_exc()
            os.kill(os.getpid(), signal.SIGINT)

            time.sleep(2.5)

else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_base.settings")

    application = get_wsgi_application()
