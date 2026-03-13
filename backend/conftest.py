"""
Shared pytest fixtures for all test suites.
"""

import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from debate_app.tests.factories import (
    UserFactory, AdminUserFactory, AnonymousUserFactory,
    DebateSessionFactory, PremiumUserFactory
)


# ---------------------------------------------------------------------------
# Patch APIClient so ALL instances (including those created in setup_method)
# never re-raise server-side exceptions — they return proper HTTP responses.
# ---------------------------------------------------------------------------
class _SafeAPIClient(APIClient):
    """APIClient that returns HTTP responses instead of raising exceptions."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('raise_request_exception', False)
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True)
def patch_api_client(monkeypatch):
    """
    Replace APIClient everywhere it's imported so setup_method() calls
    like `self.client = APIClient()` also get raise_request_exception=False.
    """
    monkeypatch.setattr('rest_framework.test.APIClient', _SafeAPIClient)
    monkeypatch.setattr('debate_app.tests.test_views.APIClient', _SafeAPIClient)


# NOTE: pgvector extension is now installed via migration
# rag_app/migrations/0000_create_pgvector_extension.py
# which runs before 0001_initial — no fixture needed here.


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return _SafeAPIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def admin_user():
    return AdminUserFactory()


@pytest.fixture
def premium_user():
    return PremiumUserFactory()


@pytest.fixture
def anon_user():
    return AnonymousUserFactory()


@pytest.fixture
def auth_client(user):
    client = _SafeAPIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = _SafeAPIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def session(user):
    return DebateSessionFactory(user=user)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Redis cache before each test to prevent cache bleed."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_gpt_response():
    from services.gpt_client import GPTResponse

    def _factory(content='Test AI response', model='gpt-4o-mini',
                  cost=0.00001, tokens=50):
        return GPTResponse(
            content=content,
            model=model,
            prompt_tokens=100,
            completion_tokens=tokens,
            cost_usd=cost,
            latency_ms=500,
        )

    return _factory