"""Session lifecycle: every JWT pair belongs to an AuthSession that can expire or be revoked."""

from datetime import timedelta
from unittest import mock

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from security.models import AuthSession
from security.sessions import SESSION_CLAIM
from security.tests.conftest import bearer
from users.factories import TEST_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

USER_URL = "/api/auth/user/"
REFRESH_URL = "/api/auth/token/refresh/"
VERIFY_URL = "/api/auth/token/verify/"
LOGOUT_URL = "/api/auth/logout/"
LOGOUT_ALL_URL = "/api/auth/logout-all/"
SESSIONS_URL = "/api/auth/sessions/"

Reason = AuthSession.RevokedReason


def frozen_at(moment):
    """Freeze Django's clock (not simplejwt's, so the tokens themselves stay unexpired)."""
    return mock.patch("django.utils.timezone.now", return_value=moment)


def session_of(token):
    return AuthSession.objects.get(pk=AccessToken(token)[SESSION_CLAIM])


@pytest.fixture
def tokens(user, login):
    response = login(HTTP_USER_AGENT="pytest-agent", REMOTE_ADDR="203.0.113.9")
    assert response.status_code == 200
    return response.data


def test_login_keeps_the_response_shape(tokens):
    assert set(tokens) == {"access", "refresh", "access_expiration", "refresh_expiration", "user"}


def test_login_opens_a_session_with_ip_and_user_agent(tokens, user):
    session = session_of(tokens["access"])
    assert session.user == user
    assert session.ip_address == "203.0.113.9"
    assert session.user_agent == "pytest-agent"
    assert RefreshToken(tokens["refresh"])[SESSION_CLAIM] == str(session.pk)


def test_refresh_expiry_is_aligned_with_the_session_cap(tokens):
    session = session_of(tokens["access"])
    exp = RefreshToken(tokens["refresh"])["exp"]
    assert exp == int((session.created_at + settings.SESSION_MAX_TTL).timestamp())


def test_access_with_a_valid_session_works(client, tokens):
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 200


def test_access_with_a_revoked_session_is_rejected_at_once(client, tokens):
    AuthSession.objects.all().revoke(Reason.ADMIN)
    response = client.get(USER_URL, **bearer(tokens["access"]))
    assert response.status_code == 401


def test_a_token_without_sid_is_rejected(client, user):
    access = RefreshToken.for_user(user).access_token
    assert client.get(USER_URL, **bearer(access)).status_code == 401


def test_refresh_keeps_the_session_and_the_response_shape(client, tokens):
    response = client.post(REFRESH_URL, {"refresh": tokens["refresh"]})
    assert response.status_code == 200
    assert set(response.data) == {"access", "access_expiration"}
    assert session_of(response.data["access"]) == session_of(tokens["access"])


def test_refresh_with_a_revoked_session_fails(client, tokens):
    AuthSession.objects.all().revoke(Reason.ADMIN)
    assert client.post(REFRESH_URL, {"refresh": tokens["refresh"]}).status_code == 401


def test_verify_rejects_a_revoked_session(client, tokens):
    assert client.post(VERIFY_URL, {"token": tokens["access"]}).status_code == 200
    AuthSession.objects.all().revoke(Reason.ADMIN)
    assert client.post(VERIFY_URL, {"token": tokens["access"]}).status_code == 401


def test_last_used_is_written_at_most_once_a_minute(client, tokens):
    session = session_of(tokens["access"])
    start = session.last_used_at

    with frozen_at(start + timedelta(seconds=30)):
        client.get(USER_URL, **bearer(tokens["access"]))
    session.refresh_from_db()
    assert session.last_used_at == start

    later = start + timedelta(minutes=2)
    with frozen_at(later):
        client.get(USER_URL, **bearer(tokens["access"]))
    session.refresh_from_db()
    assert session.last_used_at == later


def test_session_expires_after_idle_ttl(client, tokens):
    session = session_of(tokens["access"])
    with frozen_at(session.last_used_at + settings.SESSION_IDLE_TTL - timedelta(minutes=1)):
        assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 200

    session.refresh_from_db()
    with frozen_at(session.last_used_at + settings.SESSION_IDLE_TTL + timedelta(seconds=1)):
        assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401
        assert client.post(REFRESH_URL, {"refresh": tokens["refresh"]}).status_code == 401


def test_session_expires_at_max_ttl_even_if_in_use(client, tokens):
    session = session_of(tokens["access"])
    past_cap = session.created_at + settings.SESSION_MAX_TTL + timedelta(seconds=1)
    # Used a minute ago: idle is fine, only the hard cap is crossed.
    AuthSession.objects.filter(pk=session.pk).update(last_used_at=past_cap - timedelta(minutes=1))
    with frozen_at(past_cap):
        assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401


def test_logout_revokes_the_session(client, tokens):
    response = client.post(LOGOUT_URL, **bearer(tokens["access"]))
    assert response.status_code == 200
    assert response.data == {"detail": "Successfully logged out."}
    session = session_of(tokens["access"])
    assert session.revoked_reason == Reason.LOGOUT
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401


def test_logout_with_only_the_refresh_revokes_the_session(client, tokens):
    assert client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}).status_code == 200
    assert session_of(tokens["access"]).revoked_reason == Reason.LOGOUT


def test_logout_all_revokes_every_session(client, login, tokens):
    other = login().data
    response = client.post(LOGOUT_ALL_URL, **bearer(tokens["access"]))
    assert response.status_code == 200
    for pair in (tokens, other):
        assert client.get(USER_URL, **bearer(pair["access"])).status_code == 401
    assert set(AuthSession.objects.values_list("revoked_reason", flat=True)) == {Reason.LOGOUT_ALL}


def test_sessions_list_marks_the_current_one(client, login, tokens):
    login()
    response = client.get(SESSIONS_URL, **bearer(tokens["access"]))
    assert response.status_code == 200
    current = [row for row in response.data if row["current"]]
    assert len(response.data) == 2
    assert [row["id"] for row in current] == [str(session_of(tokens["access"]).pk)]


def test_sessions_list_hides_closed_sessions(client, login, tokens):
    other = login().data
    session_of(other["access"]).delete()
    AuthSession.objects.exclude(pk=session_of(tokens["access"]).pk).revoke(Reason.ADMIN)
    response = client.get(SESSIONS_URL, **bearer(tokens["access"]))
    assert len(response.data) == 1


def test_close_one_session_from_another(client, login, tokens):
    other = login().data
    other_session = session_of(other["access"])
    response = client.delete(f"{SESSIONS_URL}{other_session.pk}/", **bearer(tokens["access"]))
    assert response.status_code == 204
    assert client.get(USER_URL, **bearer(other["access"])).status_code == 401
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 200
    other_session.refresh_from_db()
    assert other_session.revoked_reason == Reason.CLOSED_BY_USER


def test_cannot_close_someone_elses_session(client, login, tokens):
    UserFactory(email="bob@test.com")
    bob_session = session_of(login("bob@test.com").data["access"])
    response = client.delete(f"{SESSIONS_URL}{bob_session.pk}/", **bearer(tokens["access"]))
    assert response.status_code == 404
    bob_session.refresh_from_db()
    assert bob_session.revoked_at is None


def test_inactive_user_cannot_log_in(login):
    UserFactory(email="off@test.com", is_active=False)
    assert login("off@test.com").status_code == 400


def test_deactivating_a_user_closes_all_sessions(client, tokens, user):
    user.is_active = False
    user.save()
    assert session_of(tokens["access"]).revoked_reason == Reason.USER_DEACTIVATED
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401


def test_deleting_a_user_invalidates_the_token(client, tokens, user):
    user.delete()
    assert not AuthSession.objects.exists()
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401


def test_saving_a_user_without_credential_changes_keeps_sessions(tokens, user):
    user.first_name = "Otra"
    user.save()
    assert session_of(tokens["access"]).revoked_at is None


@override_settings(PASSWORD_CHANGE_BY_EMAIL=False)
def test_password_change_closes_the_other_sessions(client, login, tokens):
    other = login().data
    response = client.post(
        "/api/auth/password/change/",
        {"old_password": TEST_PASSWORD, "new_password": "N3w-Passw0rd!"},
        **bearer(tokens["access"]),
    )
    assert response.status_code == 200
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 200
    assert client.get(USER_URL, **bearer(other["access"])).status_code == 401
    assert session_of(other["access"]).revoked_reason == Reason.PASSWORD_CHANGE


def test_password_reset_closes_every_session(client, tokens, user):
    client.post("/api/auth/password/recovery/", {"email": user.email})
    token = user.tokenrecovery_set.get().token
    response = client.post(
        "/api/auth/password/recovery/confirm/",
        {"email": user.email, "token": token, "password": "N3w-Passw0rd!"},
    )
    assert response.status_code == 200
    assert session_of(tokens["access"]).revoked_reason == Reason.PASSWORD_RESET
    assert client.get(USER_URL, **bearer(tokens["access"])).status_code == 401


def test_password_set_from_the_admin_closes_every_session(tokens, user):
    user.set_password("Admin-S3t!")
    user.save()
    assert session_of(tokens["access"]).revoked_reason == Reason.PASSWORD_CHANGE


def test_registration_tokens_belong_to_a_session(client):
    response = client.post(
        "/api/auth/registration/",
        {"email": "new@test.com", "password1": "Str0ng-Pass!", "password2": "Str0ng-Pass!"},
    )
    assert response.status_code == 201
    if "access" in response.data:  # only when email verification is not mandatory
        assert client.get(USER_URL, **bearer(response.data["access"])).status_code == 200


def test_expires_at_is_derived(tokens):
    session = session_of(tokens["access"])
    assert session.expires_at == min(
        session.last_used_at + settings.SESSION_IDLE_TTL,
        session.created_at + settings.SESSION_MAX_TTL,
    )
    assert session.status == "active"
    with frozen_at(timezone.now() + settings.SESSION_MAX_TTL):
        assert session.status == "expired"


def test_invalid_session_answers_401_with_its_code(client, tokens):
    AuthSession.objects.all().revoke(Reason.ADMIN)
    response = client.get(USER_URL, **bearer(tokens["access"]))
    assert response.status_code == 401
    assert response.json() == {"detail": "Session expired or closed.", "code": "session_invalid"}


def test_api_login_does_not_open_a_django_session(login, user):
    response = login()
    assert settings.SESSION_COOKIE_NAME not in response.cookies
