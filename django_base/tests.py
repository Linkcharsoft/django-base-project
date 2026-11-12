import pytest
from django.conf import settings
from rest_framework.test import APIClient

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
