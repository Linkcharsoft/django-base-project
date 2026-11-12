import pytest
from django.test import RequestFactory, override_settings

from security.client_ip import get_client_ip

CLIENT = "203.0.113.7"
PROXY_A = "10.0.1.20"


def request_with(xff=None, remote="172.18.0.5"):
    meta = {"REMOTE_ADDR": remote}
    if xff is not None:
        meta["HTTP_X_FORWARDED_FOR"] = xff
    return RequestFactory().get("/", **meta)


@override_settings(TRUSTED_PROXY_COUNT=0)
def test_no_proxy_uses_remote_addr_and_ignores_the_header():
    assert get_client_ip(request_with(xff="6.6.6.6", remote=CLIENT)) == CLIENT


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_one_proxy_takes_the_rightmost_entry():
    assert get_client_ip(request_with(xff=CLIENT)) == CLIENT


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_one_proxy_ignores_a_forged_entry_on_the_left():
    assert get_client_ip(request_with(xff=f"6.6.6.6, {CLIENT}")) == CLIENT


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_two_proxies_take_the_second_from_the_right():
    assert get_client_ip(request_with(xff=f"6.6.6.6, {CLIENT}, {PROXY_A}")) == CLIENT


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_fewer_hops_than_proxies_takes_the_leftmost():
    assert get_client_ip(request_with(xff=CLIENT)) == CLIENT


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_without_the_header_falls_back_to_remote_addr():
    """ALB health checks arrive without X-Forwarded-For."""
    assert get_client_ip(request_with(remote=PROXY_A)) == PROXY_A


@override_settings(TRUSTED_PROXY_COUNT=1)
@pytest.mark.parametrize("hop", ["unknown", "203.0.113.7:4431", "", "not-an-ip"])
def test_an_invalid_hop_returns_none(hop):
    assert get_client_ip(request_with(xff=f"{CLIENT}, {hop}")) is None


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_ipv6_is_accepted():
    assert get_client_ip(request_with(xff=" 2001:db8::1 ")) == "2001:db8::1"


@override_settings(TRUSTED_PROXY_COUNT=1)
@pytest.mark.django_db
def test_a_forged_header_does_not_break_the_login(client):
    response = client.post(
        "/api/auth/login/",
        {"email": "x@test.com", "password": "x"},
        HTTP_X_FORWARDED_FOR="unknown",
    )
    assert response.status_code == 400
