import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """DRF's anon/user throttles count in the cache; without this they leak between tests."""
    cache.clear()
    yield
    cache.clear()
