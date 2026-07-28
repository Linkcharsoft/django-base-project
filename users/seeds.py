from users.factories import TEST_PASSWORD, UserFactory

# Enough to exercise pagination (default page size 10, max 100).
BULK_USERS = 50

# One account per auth state the API can be in. Keep this table in sync with
# docs/seed-data.md — the frontend reads that table, not this file.
PERSONAS = [
    {"email": "admin@test.com", "username": "admin", "is_staff": True, "is_superuser": True},
    {"email": "user@test.com", "register_complete": True},
    {"email": "incomplete@test.com", "register_complete": False},
    {"email": "unverified@test.com", "verified": False},
    {"email": "blocked@test.com", "is_active": False},
]


def seed():
    for persona in PERSONAS:
        UserFactory(**{"register_complete": True, **persona})
    UserFactory.create_batch(BULK_USERS, register_complete=True)
    return f"{len(PERSONAS) + BULK_USERS} users (password for all: {TEST_PASSWORD})"
