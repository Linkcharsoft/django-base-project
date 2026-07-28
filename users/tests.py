import pytest
from rest_framework.test import APIClient

from users.factories import TEST_PASSWORD, UserFactory


@pytest.mark.django_db
def test_users_list_is_admin_only():
    client = APIClient()
    client.force_authenticate(user=UserFactory(is_staff=False))
    response = client.get("/api/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_users_list_allows_staff():
    client = APIClient()
    client.force_authenticate(user=UserFactory(is_staff=True))
    response = client.get("/api/users/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_factory_is_idempotent_on_email():
    """`django_get_or_create` on email is what keeps `just seed` re-runnable."""
    first = UserFactory(email="repeated@test.com")
    second = UserFactory(email="repeated@test.com")

    assert first.pk == second.pk


@pytest.mark.django_db
def test_factory_flags_drive_account_state():
    """The three post_generation flags the seed personas rely on."""
    user = UserFactory(email="flags@test.com", verified=False, register_complete=False)

    assert user.check_password(TEST_PASSWORD)
    assert not user.emailaddress_set.get(email=user.email).verified
    assert not user.profile.is_register_complete
