import logging

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.utils.translation import gettext as _

from platform_configurations.models import SystemStatus

logger = logging.getLogger(__name__)

DEFAULT_EXEMPT_PATHS = (
    "/admin/",
    "/api/system-status/",
    "/api/schema/",
    "/static/",
    "/media/",
    "/__debug__/",
)


class IsSystemUpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = getattr(settings, "SYSTEM_STATUS_EXEMPT_PATHS", DEFAULT_EXEMPT_PATHS)

    def _is_exempt(self, request):
        if any(request.path.startswith(p) for p in self.exempt_paths):
            return True
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_superuser)

    def __call__(self, request):
        if self._is_exempt(request):
            return self.get_response(request)

        try:
            status = SystemStatus.get_status()
        except (OperationalError, ProgrammingError):
            # Tabla todavía no existe (primer migrate, CI con DB fresca).
            logger.warning("SystemStatus table unavailable — bypassing maintenance check")
            return self.get_response(request)

        if not status.is_operational:
            return JsonResponse({"error": _("The system is under maintenance")}, status=503)

        return self.get_response(request)
