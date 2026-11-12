import pytest
from rest_framework.test import APIClient

from users.factories import TEST_PASSWORD, UserFactory

LOGIN_URL = "/api/auth/login/"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email="ana@test.com")


@pytest.fixture
def login(client):
    """POST the login form and return the response (``login(email, password, **extra)``)."""

    def _login(email="ana@test.com", password=TEST_PASSWORD, **extra):
        return client.post(LOGIN_URL, {"email": email, "password": password}, **extra)

    return _login


def bearer(access):
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}
