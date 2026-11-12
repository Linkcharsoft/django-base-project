"""LoginEvent log and the login rate limit, shared by the API and the admin login."""

import pytest
from django.test import Client, override_settings

from security.models import LoginEvent
from users.factories import TEST_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

Reason = LoginEvent.Reason
Source = LoginEvent.Source
ADMIN_LOGIN_URL = "/admin/login/"


def admin_login(email, password=TEST_PASSWORD, ip="198.51.100.1"):
    return Client(REMOTE_ADDR=ip).post(
        ADMIN_LOGIN_URL, {"username": email, "password": password, "next": "/admin/"}
    )


def last_event():
    return LoginEvent.objects.first()


# <---------------------- Reasons (API) ---------------------->


def test_successful_login_is_recorded(user, login):
    login(HTTP_USER_AGENT="pytest-agent")
    event = last_event()
    assert (event.reason, event.source, event.user, event.email) == (
        Reason.OK,
        Source.API,
        user,
        "ana@test.com",
    )
    assert event.user_agent == "pytest-agent"
    assert event.ip_address == "127.0.0.1"


def test_bad_password(user, login):
    assert login(password="wrong").status_code == 400
    assert (last_event().reason, last_event().user) == (Reason.BAD_PASSWORD, user)


def test_unknown_email(login, db):
    assert login("ghost@test.com").status_code == 400
    assert (last_event().reason, last_event().user) == (Reason.UNKNOWN_EMAIL, None)


def test_inactive_user(login):
    UserFactory(email="off@test.com", is_active=False)
    login("off@test.com")
    assert last_event().reason == Reason.INACTIVE


def test_missing_password_is_invalid(client, db):
    assert client.post("/api/auth/login/", {"email": "ana@test.com"}).status_code == 400
    assert last_event().reason == Reason.INVALID


@override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
def test_unverified_email(login):
    UserFactory(email="pending@test.com", verified=False)
    assert login("pending@test.com").status_code == 400
    assert last_event().reason == Reason.EMAIL_NOT_VERIFIED


def test_email_is_normalized(user, login):
    login("  ANA@Test.com ")
    assert last_event().email == "ana@test.com"


# <---------------------- Rate limit ---------------------->


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=3)
def test_limit_per_email_answers_429_and_records_throttled(user, login):
    for _ in range(3):
        assert login(password="wrong").status_code == 400
    response = login()  # even the right password is blocked
    assert response.status_code == 429
    assert last_event().reason == Reason.THROTTLED
    assert last_event().user == user


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=3)
def test_throttled_attempts_keep_counting(user, login):
    for _ in range(3):
        login(password="wrong")
    login()
    # Moving the window back by the 3 failures alone would unblock it; the throttled one counts.
    LoginEvent.objects.filter(reason=Reason.BAD_PASSWORD).order_by("created_at").first().delete()
    assert login().status_code == 429


@override_settings(LOGIN_RATE_LIMIT_PER_IP=3)
def test_limit_per_ip_across_emails(login, db):
    for n in range(3):
        login(f"nobody{n}@test.com")
    assert login("another@test.com").status_code == 429


@override_settings(LOGIN_RATE_LIMIT_PER_IP=3)
def test_limit_per_ip_does_not_block_other_ips(login, db):
    for n in range(3):
        login(f"nobody{n}@test.com")
    assert login("another@test.com", REMOTE_ADDR="192.0.2.50").status_code == 400


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=3)
def test_attempts_outside_the_window_do_not_count(user, login):
    for _ in range(3):
        login(password="wrong")
    LoginEvent.objects.update(created_at="2000-01-01T00:00:00Z")
    assert login().status_code == 200


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=3)
def test_limit_is_shared_from_the_api_to_the_admin(login):
    UserFactory(email="staff@test.com", is_staff=True)
    for _ in range(3):
        login("staff@test.com", password="wrong")
    response = admin_login("staff@test.com")
    assert response.status_code == 429
    assert (last_event().reason, last_event().source) == (Reason.THROTTLED, Source.ADMIN)


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=3)
def test_limit_is_shared_from_the_admin_to_the_api(login):
    UserFactory(email="staff@test.com", is_staff=True)
    for _ in range(3):
        admin_login("staff@test.com", password="wrong")
    assert login("staff@test.com").status_code == 429
    assert (last_event().reason, last_event().source) == (Reason.THROTTLED, Source.API)


# <---------------------- Admin login ---------------------->


def test_admin_login_success_is_recorded(db):
    staff = UserFactory(email="staff@test.com", is_staff=True)
    response = admin_login("staff@test.com")
    assert response.status_code == 302
    assert (last_event().reason, last_event().source, last_event().user) == (
        Reason.OK,
        Source.ADMIN,
        staff,
    )


def test_admin_login_not_staff(user):
    response = admin_login("ana@test.com")
    assert response.status_code == 200  # the form again, with its usual error
    assert (last_event().reason, last_event().source) == (Reason.NOT_STAFF, Source.ADMIN)


def test_admin_login_bad_password(db):
    UserFactory(email="staff@test.com", is_staff=True)
    admin_login("staff@test.com", password="wrong")
    assert last_event().reason == Reason.BAD_PASSWORD


@override_settings(LOGIN_RATE_LIMIT_PER_EMAIL=2)
def test_admin_login_throttled_shows_the_form_error(db):
    UserFactory(email="staff@test.com", is_staff=True)
    admin_login("staff@test.com", password="wrong")
    admin_login("staff@test.com", password="wrong")
    response = admin_login("staff@test.com")
    assert response.status_code == 429
    assert b"Too many login attempts" in response.content


def test_admin_login_page_still_renders(db):
    assert Client().get(ADMIN_LOGIN_URL).status_code == 200


# <---------------------- allauth HTML views are gone ---------------------->


@pytest.mark.parametrize(
    "path",
    ["/api/auth/allauth/login/", "/api/auth/allauth/signup/", "/api/auth/allauth/password/reset/"],
)
def test_allauth_html_views_are_not_mounted(path, db):
    assert Client().get(path).status_code == 404


def test_registration_still_sends_the_verification_mail(client, db, mailoutbox):
    response = client.post(
        "/api/auth/registration/",
        {"email": "new@test.com", "password1": "Str0ng-Pass!", "password2": "Str0ng-Pass!"},
    )
    assert response.status_code == 201
    assert len(mailoutbox) == 1
    assert "/registro/validar-email/" in mailoutbox[0].body
