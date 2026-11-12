import re

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.urls import URLResolver, get_resolver
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from django_base.settings.environment_variables import with_www_variant
from users.factories import UserFactory


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://app.com", ["https://app.com", "https://www.app.com"]),
        ("https://www.app.com", ["https://www.app.com", "https://app.com"]),
        ("https://app.com:8443", ["https://app.com:8443", "https://www.app.com:8443"]),
    ],
)
def test_with_www_variant_toggles_www(url, expected):
    assert with_www_variant(url) == expected


@pytest.mark.parametrize("url", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_with_www_variant_skips_local_hosts(url):
    assert with_www_variant(url) == [url]


# <---------------------- Public surface ---------------------->
# The API is private by default (DEFAULT_PERMISSION_CLASSES = IsAuthenticated). This is the
# complete list of what an anonymous client may call; a new public endpoint must be added here
# on purpose, with AllowAny declared explicitly on the view.

PUBLIC_ENDPOINTS = {
    ("POST", "/api/auth/login/"),
    ("GET", "/api/auth/logout/"),  # dj-rest-auth: 405 unless ACCOUNT_LOGOUT_ON_GET
    ("POST", "/api/auth/logout/"),  # also accepts just the refresh, after the access expired
    ("POST", "/api/auth/token/refresh/"),
    ("POST", "/api/auth/token/verify/"),
    ("POST", "/api/auth/password/recovery/"),
    ("POST", "/api/auth/password/recovery/check-token/"),
    ("POST", "/api/auth/password/recovery/confirm/"),
    ("POST", "/api/auth/registration/"),
    ("GET", "/api/auth/registration/verify-email/"),  # dj-rest-auth: always 405
    ("POST", "/api/auth/registration/verify-email/"),
    ("POST", "/api/auth/registration/resend-email/"),
    ("GET", "/api/schema/"),
    ("GET", "/api/schema/swagger-ui/"),
    ("GET", "/api/schema/redoc/"),
    ("GET", "/api/system-status/"),
    ("GET", "/api/system-status/is-system-up/"),
}

_GROUP = re.compile(r"\(\?P<(\w+)>[^)]*\)")
_CONVERTER = re.compile(r"<(?:\w+:)?(\w+)>")
_HTTP_METHODS = ("get", "post", "patch", "put", "delete")


def _drf_routes(patterns=None, prefix=""):
    """(route, view callback) for every DRF view, routes written as /api/users/{pk}/."""
    for pattern in get_resolver().url_patterns if patterns is None else patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from _drf_routes(pattern.url_patterns, route)
            continue
        if getattr(pattern.callback, "cls", None) is None or "format" in route:
            continue
        route = _CONVERTER.sub(r"{\1}", _GROUP.sub(r"{\1}", route))
        yield "/" + route.replace("^", "").replace("$", "").replace("/?", "/"), pattern.callback


def _anonymous_allowed(callback, method):
    request = Request(APIRequestFactory().generic(method, "/"))
    request.user = AnonymousUser()
    view = callback.cls(**getattr(callback, "initkwargs", {}))
    view.request, view.kwargs, view.format_kwarg = request, {}, None
    actions = getattr(callback, "actions", None)
    if actions:
        view.action = actions[method.lower()]
    return all(p.has_permission(request, view) for p in view.get_permissions())


def _anonymous_endpoints():
    found = set()
    for route, callback in _drf_routes():
        actions = getattr(callback, "actions", None)
        methods = actions or [m for m in _HTTP_METHODS if hasattr(callback.cls, m)]
        for method in methods:
            if method == "put":  # disabled project-wide (NoPutViewSetMixin)
                continue
            if _anonymous_allowed(callback, method.upper()):
                found.add((method.upper(), route))
    return found


def test_public_endpoints_are_exactly_the_allowed_list():
    assert _anonymous_endpoints() == PUBLIC_ENDPOINTS


@pytest.mark.django_db
def test_a_private_endpoint_without_token_answers_401():
    assert APIClient().get("/api/auth/sessions/").status_code == 401


# <---------------------- Throttle scopes ---------------------->


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/auth/login/"),
        ("post", "/api/auth/logout/"),
        ("post", "/api/auth/registration/"),
        ("post", "/api/auth/password/change/"),
    ],
)
def test_dj_rest_auth_views_have_a_throttle_rate(method, path):
    """dj-rest-auth's views declare throttle_scope='dj_rest_auth'; with ScopedRateThrottle on and
    no rate for that scope they answer 500. A library adding a new scope fails here too."""
    assert (
        "rest_framework.throttling.ScopedRateThrottle"
        in (settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])
    )
    client = APIClient()
    client.force_authenticate(UserFactory(email="throttle@test.com"))
    response = getattr(client, method)(path, {})
    assert response.status_code < 500
