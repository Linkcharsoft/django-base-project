import factory
from allauth.account.models import EmailAddress
from factory.django import DjangoModelFactory

from users.models import User

# Shared by every seeded account so the frontend can hardcode it.
TEST_PASSWORD = "Test1234!"


class UserFactory(DjangoModelFactory):
    """Test/seed user. Idempotent on ``email``, so re-running the seed is safe.

    Three keyword flags beyond the model fields:

    - ``password="..."``      → defaults to ``TEST_PASSWORD``
    - ``verified=False``      → leaves the allauth ``EmailAddress`` unverified
    - ``register_complete``   → sets ``profile.is_register_complete``
    """

    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    username = factory.LazyAttribute(lambda o: o.email.split("@")[0])
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_test_user = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or TEST_PASSWORD)
        obj.save(update_fields=["password"])

    @factory.post_generation
    def verified(obj, create, extracted, **kwargs):
        # Without a verified EmailAddress row allauth refuses the login, so the
        # default has to be True — an unverified user is the explicit exception.
        EmailAddress.objects.update_or_create(
            user=obj,
            email=obj.email,
            defaults={"verified": True if extracted is None else extracted, "primary": True},
        )

    @factory.post_generation
    def register_complete(obj, create, extracted, **kwargs):
        # Profile is created by the post_save signal on User, never here.
        if extracted is not None:
            obj.profile.is_register_complete = extracted
            obj.profile.save(update_fields=["is_register_complete"])
