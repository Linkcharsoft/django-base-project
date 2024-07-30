from django.http import JsonResponse
from django.urls import resolve
from django.utils.translation import gettext as _
from platform_configurations.models import SystemStatus


class IsSystemUpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resolver_match = resolve(request.path)

        if (
            resolver_match.url_name
            and resolver_match.app_name == "admin"
            or resolver_match.route == "api/system-status/is-system-up/$"
            or request.user.is_superuser
        ):
            return self.get_response(request)

        status = SystemStatus.get_status()
        if not status.is_operational:
            return JsonResponse(
                {"error": _("The system is under maintenance")}, status=503
            )

        response = self.get_response(request)
        return response
