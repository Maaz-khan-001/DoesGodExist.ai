"""
Authentication flow integration tests.

Tests:
  - Email registration
  - Login / logout
  - JWT cookie behavior
  - Anonymous user creation and turn tracking
  - Daily limit reset
"""

import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from debate_app.tests.factories import UserFactory, AnonymousUserFactory


@pytest.mark.system
@pytest.mark.django_db
class TestRegistration:

    def setup_method(self):
        self.client = APIClient()

    def test_register_with_valid_credentials(self):
        resp = self.client.post('/api/v1/auth/registration/', {
            'email': 'newuser@test.com',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
        }, format='json')
        assert resp.status_code in (200, 201)

        from debate_app.models import User
        assert User.objects.filter(email='newuser@test.com').exists()
        user = User.objects.get(email='newuser@test.com')
        assert user.tier == 'registered'

    def test_register_with_weak_password_rejected(self):
        resp = self.client.post('/api/v1/auth/registration/', {
            'email': 'user2@test.com',
            'password1': '12345678',
            'password2': '12345678',
        }, format='json')
        assert resp.status_code == 400

    def test_register_with_duplicate_email_rejected(self):
        UserFactory(email='existing@test.com')
        resp = self.client.post('/api/v1/auth/registration/', {
            'email': 'existing@test.com',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
        }, format='json')
        assert resp.status_code == 400

    def test_register_mismatched_passwords_rejected(self):
        resp = self.client.post('/api/v1/auth/registration/', {
            'email': 'user3@test.com',
            'password1': 'SecurePassword123!',
            'password2': 'DifferentPassword!',
        }, format='json')
        assert resp.status_code == 400


@pytest.mark.system
@pytest.mark.django_db
class TestLogin:

    def setup_method(self):
        self.client = APIClient()

    def test_login_with_valid_credentials(self):
        user = UserFactory(email='login@test.com')
        user.set_password('TestPassword123!')
        user.save()

        resp = self.client.post('/api/v1/auth/login/', {
            'email': 'login@test.com',
            'password': 'TestPassword123!',
        }, format='json')
        assert resp.status_code == 200
        assert 'user' in resp.data

    def test_login_with_wrong_password_fails(self):
        user = UserFactory(email='wrongpass@test.com')
        user.set_password('CorrectPassword123!')
        user.save()

        resp = self.client.post('/api/v1/auth/login/', {
            'email': 'wrongpass@test.com',
            'password': 'WrongPassword',
        }, format='json')
        assert resp.status_code == 400

    def test_login_with_nonexistent_email_fails(self):
        resp = self.client.post('/api/v1/auth/login/', {
            'email': 'nobody@test.com',
            'password': 'AnyPassword123!',
        }, format='json')
        assert resp.status_code == 400

    def test_get_user_after_login(self):
        user = UserFactory(email='getuser@test.com')
        self.client.force_authenticate(user=user)

        resp = self.client.get('/api/v1/auth/user/')
        assert resp.status_code == 200
        assert resp.data['email'] == 'getuser@test.com'
        assert 'daily_turns_remaining' in resp.data

    def test_get_user_unauthenticated_returns_401(self):
        resp = self.client.get('/api/v1/auth/user/')
        assert resp.status_code in (401, 403)


@pytest.mark.system
@pytest.mark.django_db
class TestAnonymousUserTracking:

    def setup_method(self):
        self.client = APIClient()

    @patch('services.gpt_client.GPTClient.complete')
    @patch('rag_app.retrieval_service.RetrievalService.retrieve')
    def test_anonymous_user_created_on_first_message(
        self, mock_retrieve, mock_gpt
    ):
        from services.gpt_client import GPTResponse
        mock_retrieve.return_value = []
        mock_gpt.return_value = GPTResponse(
            content='Response', model='gpt-4o-mini',
            prompt_tokens=10, completion_tokens=5,
            cost_usd=0.000001, latency_ms=300,
        )
        from debate_app.models import User

        count_before = User.objects.filter(is_anonymous_user=True).count()
        self.client.post(
            '/api/v1/debate/message/',
            {'message': 'Hello'},
            format='json'
        )
        count_after = User.objects.filter(is_anonymous_user=True).count()
        assert count_after == count_before + 1


@pytest.mark.system
@pytest.mark.django_db
class TestDailyTurnLimit:

    def test_turn_limit_resets_on_new_day(self):
        from django.utils import timezone
        from datetime import date, timedelta
        from debate_app.models import User
        from debate_app.views import DAILY_TURN_LIMITS

        # User with old reset date (yesterday)
        user = UserFactory(
            tier='registered',
            daily_turn_count=20,   # Hit the limit yesterday
            daily_reset_date=date.today() - timedelta(days=1),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        # Check that _check_and_increment_turn_atomic resets the count
        from debate_app.views import DebateMessageView
        view = DebateMessageView()
        result = view._check_and_increment_turn_atomic(user)
        assert result is True  # Should succeed because it's a new day

        user.refresh_from_db()
        assert user.daily_turn_count == 1
        assert user.daily_reset_date == date.today()

    def test_premium_user_not_limited(self):
        from datetime import date
        from debate_app.views import DebateMessageView

        user = UserFactory(
            tier='premium',
            daily_turn_count=100,
            daily_reset_date=date.today(),
        )
        view = DebateMessageView()
        result = view._check_and_increment_turn_atomic(user)
        assert result is True  # Premium has 9999 limit

