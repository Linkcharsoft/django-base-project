from django.http import HttpResponse
from django.utils.translation import gettext as _


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ["/", "/healthcheck/"]:
            return HttpResponse("ok")
        return self.get_response(request)
