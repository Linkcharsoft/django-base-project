"""Security admin section: summary, actions, read-only login attempts, user columns."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone

from security.management.commands.purge_security_records import purge_security_records
from security.models import AuthSession, LoginEvent
from security.sessions import open_session
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

Reason = LoginEvent.Reason
SUMMARY_URL = "/admin/security/securitysummary/"
SESSIONS_URL = "/admin/security/authsession/"
EVENTS_URL = "/admin/security/loginevent/"
USERS_URL = "/admin/users/user/"


@pytest.fixture
def admin_client():
    client = Client()
    client.force_login(UserFactory(email="root@test.com", is_staff=True, is_superuser=True))
    return client


def fail(email, ip="198.51.100.7", user=None, days_ago=0, reason=Reason.BAD_PASSWORD):
    return LoginEvent.objects.create(
        email=email,
        user=user,
        reason=reason,
        ip_address=ip,
        created_at=timezone.now() - timedelta(days=days_ago),
    )


def test_section_lists_sessions_attempts_and_summary(admin_client):
    content = admin_client.get("/admin/security/").content.decode()
    assert "Security" in content
    for url in (SESSIONS_URL, EVENTS_URL, SUMMARY_URL):
        assert url in content


def test_summary_shows_users_on_alert_and_failing_ips(admin_client):
    victim = UserFactory(email="victim@test.com")
    calm = UserFactory(email="calm@test.com")
    for _ in range(settings.SECURITY_FAILED_LOGINS_ALERT):
        fail(victim.email, user=victim)
    fail(calm.email, user=calm, ip="192.0.2.99")

    response = admin_client.get(SUMMARY_URL)
    assert response.status_code == 200
    assert [u.email for u in response.context["alert_users"]] == ["victim@test.com"]
    ips = {row["ip_address"]: row["failed"] for row in response.context["top_ips"]}
    assert ips == {"198.51.100.7": 5, "192.0.2.99": 1}


def test_summary_ignores_failures_outside_the_window(admin_client):
    victim = UserFactory(email="victim@test.com")
    window = settings.SECURITY_FAILED_LOGINS_WINDOW.days
    for _ in range(settings.SECURITY_FAILED_LOGINS_ALERT):
        fail(victim.email, user=victim, days_ago=window + 1)
    response = admin_client.get(SUMMARY_URL)
    assert list(response.context["alert_users"]) == []
    assert list(response.context["top_ips"]) == []


def test_summary_alert_needs_the_threshold(admin_client):
    victim = UserFactory(email="victim@test.com")
    for _ in range(settings.SECURITY_FAILED_LOGINS_ALERT - 1):
        fail(victim.email, user=victim)
    fail(victim.email, user=victim, reason=Reason.OK)  # successes do not count
    assert list(admin_client.get(SUMMARY_URL).context["alert_users"]) == []


def test_summary_is_staff_only():
    client = Client()
    client.force_login(UserFactory(email="plain@test.com"))
    assert client.get(SUMMARY_URL).status_code == 302  # to the admin login


def test_close_session_action(admin_client):
    user = UserFactory(email="ana@test.com")
    session, _refresh = open_session(user)
    response = admin_client.post(
        SESSIONS_URL, {"action": "close_sessions", "_selected_action": [str(session.pk)]}
    )
    assert response.status_code == 302
    session.refresh_from_db()
    assert session.revoked_reason == AuthSession.RevokedReason.ADMIN


def test_sessions_filter_by_status(admin_client):
    user = UserFactory(email="ana@test.com")
    active, _ = open_session(user)
    revoked, _ = open_session(user)
    AuthSession.objects.filter(pk=revoked.pk).revoke(AuthSession.RevokedReason.ADMIN)
    expired, _ = open_session(user)
    AuthSession.objects.filter(pk=expired.pk).update(
        last_used_at=timezone.now() - settings.SESSION_IDLE_TTL - timedelta(minutes=1)
    )
    for status, expected in (("active", active), ("revoked", revoked), ("expired", expired)):
        response = admin_client.get(SESSIONS_URL, {"status": status})
        assert [s.pk for s in response.context["cl"].result_list] == [expected.pk]


def test_sessions_search_by_email_and_ip(admin_client):
    user = UserFactory(email="ana@test.com")
    session, _ = open_session(user)
    AuthSession.objects.filter(pk=session.pk).update(ip_address="203.0.113.5")
    open_session(UserFactory(email="bob@test.com"))
    for query in ("ana@test", "203.0.113.5"):
        result = admin_client.get(SESSIONS_URL, {"q": query}).context["cl"].result_list
        assert [s.pk for s in result] == [session.pk]


def test_close_all_sessions_of_a_user(admin_client):
    user = UserFactory(email="ana@test.com")
    open_session(user)
    open_session(user)
    admin_client.post(
        USERS_URL, {"action": "close_all_sessions", "_selected_action": [str(user.pk)]}
    )
    assert not AuthSession.objects.valid().filter(user=user).exists()


def test_user_list_shows_security_columns_and_alert_filter(admin_client):
    victim = UserFactory(email="victim@test.com")
    UserFactory(email="calm@test.com")
    open_session(victim)
    for _ in range(settings.SECURITY_FAILED_LOGINS_ALERT):
        fail(victim.email, user=victim)

    response = admin_client.get(USERS_URL, {"security_alert": "yes"})
    users = list(response.context["cl"].result_list)
    assert [u.email for u in users] == ["victim@test.com"]
    assert (users[0].active_sessions, users[0].failed_logins) == (1, 5)


def test_user_change_page_shows_the_sessions_inline(admin_client):
    user = UserFactory(email="ana@test.com")
    open_session(user, user_agent="inline-agent")
    response = admin_client.get(f"{USERS_URL}{user.pk}/change/")
    assert b"inline-agent" in response.content


def test_login_attempts_are_read_only(admin_client):
    event = fail("ana@test.com")
    assert admin_client.get(f"{EVENTS_URL}add/").status_code == 403
    assert admin_client.get(f"{EVENTS_URL}{event.pk}/delete/").status_code == 403
    response = admin_client.post(f"{EVENTS_URL}{event.pk}/change/", {"email": "changed@x.com"})
    assert response.status_code == 403
    event.refresh_from_db()
    assert event.email == "ana@test.com"


def test_login_attempts_filters_and_search(admin_client):
    fail("ana@test.com")
    fail("bob@test.com", ip="192.0.2.1", reason=Reason.UNKNOWN_EMAIL)
    by_reason = admin_client.get(EVENTS_URL, {"reason": Reason.UNKNOWN_EMAIL})
    assert [e.email for e in by_reason.context["cl"].result_list] == ["bob@test.com"]
    by_ip = admin_client.get(EVENTS_URL, {"q": "192.0.2.1"})
    assert [e.email for e in by_ip.context["cl"].result_list] == ["bob@test.com"]


# <---------------------- Purge ---------------------->


def test_purge_deletes_old_events_and_ended_sessions():
    user = UserFactory(email="ana@test.com")
    now = timezone.now()
    old_event = fail("a@test.com", days_ago=settings.LOGIN_EVENT_RETENTION.days + 1)
    recent_event = fail("a@test.com", days_ago=1)

    live, _ = open_session(user)
    revoked_long_ago, _ = open_session(user)
    revoked_recently, _ = open_session(user)
    idle_long_ago, _ = open_session(user)
    long_ago = now - settings.AUTH_SESSION_RETENTION - timedelta(days=1)
    AuthSession.objects.filter(pk=revoked_long_ago.pk).update(revoked_at=long_ago)
    AuthSession.objects.filter(pk=revoked_recently.pk).update(revoked_at=now)
    AuthSession.objects.filter(pk=idle_long_ago.pk).update(
        last_used_at=long_ago - settings.SESSION_IDLE_TTL
    )

    assert purge_security_records(now) == (1, 2)
    assert set(LoginEvent.objects.values_list("pk", flat=True)) == {recent_event.pk}
    assert old_event.pk not in LoginEvent.objects.values_list("pk", flat=True)
    assert set(AuthSession.objects.values_list("pk", flat=True)) == {live.pk, revoked_recently.pk}
