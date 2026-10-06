import pytest

from django_base.settings.environment_variables import with_www_variant


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
