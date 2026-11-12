"""The Django admin login, with the same rate limit and LoginEvent log as the API login.

Mounted on ``admin/login/`` ahead of ``admin.site.urls`` (see ``django_base/urls.py``). Attempts
here and on ``/api/auth/login/`` count against the same per-IP and per-email limits.
"""

from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from security.login_attempts import (
    classify_failure,
    is_rate_limited,
    normalize_email,
    record_login_event,
)
from security.models import LoginEvent

ADMIN = LoginEvent.Source.ADMIN
THROTTLED_MESSAGE = gettext_lazy("Too many login attempts. Wait a minute and try again.")
TOO_MANY_REQUESTS = 429


def _throttled_response(request, username):
    form = AdminAuthenticationForm(request, initial={"username": username})
    form._errors = ErrorDict(
        {NON_FIELD_ERRORS: form.error_class([THROTTLED_MESSAGE], error_class="nonfield")}
    )
    context = {
        **admin.site.each_context(request),
        "title": _("Log in"),
        "subtitle": None,
        "app_path": request.get_full_path(),
        "username": request.user.get_username(),
        "form": form,
        REDIRECT_FIELD_NAME: request.GET.get(REDIRECT_FIELD_NAME, ""),
    }
    return TemplateResponse(
        request,
        admin.site.login_template or "admin/login.html",
        context,
        status=TOO_MANY_REQUESTS,
    )


@sensitive_post_parameters()
@csrf_protect
@never_cache
def admin_login(request, extra_context=None):
    if request.method != "POST":
        return admin.site.login(request, extra_context)

    username = normalize_email(request.POST.get("username"))
    if is_rate_limited(request, username):
        record_login_event(request, LoginEvent.Reason.THROTTLED, username, source=ADMIN)
        return _throttled_response(request, username)

    response = admin.site.login(request, extra_context)
    user = request.user
    if response.status_code == 302 and user.is_authenticated and user.is_staff:
        record_login_event(request, LoginEvent.Reason.OK, username, user=user, source=ADMIN)
    else:
        reason, known_user = classify_failure(username, request.POST.get("password"), ADMIN)
        record_login_event(request, reason, username, user=known_user, source=ADMIN)
    return response
