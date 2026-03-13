import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from rest_framework.test import APIClient

from analytics_app.models import GPTLog, BudgetAlert, MonthlyBudget
from analytics_app.budget_guard import BudgetGuard, BUDGET_CUTOFF_REDIS_KEY
from debate_app.tests.factories import (
    UserFactory, AdminUserFactory, DebateSessionFactory, AssistantMessageFactory
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_gpt_log(session, cost='0.001000', model='gpt-4o-mini', tokens=100):
    msg = AssistantMessageFactory(session=session)
    return GPTLog.objects.create(
        session=session,
        message=msg,
        model_used=model,
        prompt_tokens=80,
        completion_tokens=20,
        total_tokens=tokens,
        cost_usd=Decimal(cost),
        latency_ms=300,
    )


def make_monthly_budget(cost='10.00', tokens=1000, messages=5, sessions=2):
    now = timezone.now()
    month_start = now.date().replace(day=1)
    return MonthlyBudget.objects.create(
        month=month_start,
        total_cost_usd=Decimal(cost),
        total_tokens=tokens,
        total_messages=messages,
        total_sessions=sessions,
    )


# ── Model tests ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGPTLogModel:

    def test_gpt_log_created_with_correct_fields(self):
        session = DebateSessionFactory()
        log = make_gpt_log(session, cost='0.002500', model='gpt-4o', tokens=200)

        assert log.model_used == 'gpt-4o'
        assert log.cost_usd == Decimal('0.002500')
        assert log.total_tokens == 200
        assert log.cache_hit is False
        assert log.error is None

    def test_gpt_log_uuid_primary_key(self):
        session = DebateSessionFactory()
        log = make_gpt_log(session)
        assert log.id is not None
        assert len(str(log.id)) == 36  # UUID format

    def test_gpt_log_indexes_on_created_at_and_session(self):
        # Just verify model can be queried via those fields
        session = DebateSessionFactory()
        make_gpt_log(session)
        assert GPTLog.objects.filter(session=session).count() == 1
        assert GPTLog.objects.filter(created_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestBudgetAlertModel:

    def test_budget_alert_created(self):
        now = timezone.now()
        alert = BudgetAlert.objects.create(
            month=now.date().replace(day=1),
            total_cost_usd=Decimal('150.00'),
            alert_level='50pct',
            is_cutoff_active=False,
        )
        assert alert.alert_level == '50pct'
        assert alert.is_cutoff_active is False

    def test_unique_together_month_and_level(self):
        from django.db import IntegrityError
        now = timezone.now()
        month = now.date().replace(day=1)
        BudgetAlert.objects.create(
            month=month,
            total_cost_usd=Decimal('150.00'),
            alert_level='50pct',
        )
        with pytest.raises(IntegrityError):
            BudgetAlert.objects.create(
                month=month,
                total_cost_usd=Decimal('155.00'),
                alert_level='50pct',  # duplicate month+level
            )

    def test_different_levels_in_same_month_allowed(self):
        now = timezone.now()
        month = now.date().replace(day=1)
        BudgetAlert.objects.create(month=month, total_cost_usd=Decimal('150'), alert_level='50pct')
        BudgetAlert.objects.create(month=month, total_cost_usd=Decimal('240'), alert_level='80pct')
        assert BudgetAlert.objects.filter(month=month).count() == 2


@pytest.mark.django_db
class TestMonthlyBudgetModel:

    def test_monthly_budget_created(self):
        mb = make_monthly_budget(cost='25.50', tokens=5000)
        assert mb.total_cost_usd == Decimal('25.50')
        assert mb.total_tokens == 5000

    def test_status_ok_below_50pct(self):
        mb = make_monthly_budget(cost='10.00')  # 10/300 = 3.3%
        assert mb.status == 'ok'

    def test_status_warning_at_50pct(self):
        mb = make_monthly_budget(cost='150.00')  # 150/300 = 50%
        assert mb.status == 'warning'

    def test_status_critical_at_80pct(self):
        mb = make_monthly_budget(cost='240.00')  # 240/300 = 80%
        assert mb.status == 'critical'

    def test_status_cutoff_at_100pct(self):
        mb = make_monthly_budget(cost='300.00')  # 300/300 = 100%
        assert mb.status == 'cutoff'

    def test_status_cutoff_over_100pct(self):
        mb = make_monthly_budget(cost='350.00')
        assert mb.status == 'cutoff'


# ── BudgetGuard tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBudgetGuard:


    def _make_logs_totalling(self, total_cost: float):
        """
        cost_usd is DecimalField(max_digits=8, decimal_places=6) → max 99.999999.
        Use many logs of 1.0 each so no single log overflows the field.
        """
        session = DebateSessionFactory()
        for _ in range(int(total_cost)):
            make_gpt_log(session, cost='1.000000')






    def test_no_alert_below_50pct(self):
        self._make_logs_totalling(100)  # 100/300 = 33%
        BudgetGuard().check()
        assert BudgetAlert.objects.count() == 0

    def test_50pct_alert_created(self):
        self._make_logs_totalling(160)  # 160/300 = 53%
        with patch.object(BudgetGuard, '_send_alert'):
            BudgetGuard().check()
        assert BudgetAlert.objects.filter(alert_level='50pct').exists()

    def test_80pct_alert_created(self):
        self._make_logs_totalling(250)  # 250/300 = 83%
        with patch.object(BudgetGuard, '_send_alert'):
            BudgetGuard().check()
        assert BudgetAlert.objects.filter(alert_level='80pct').exists()
        assert BudgetAlert.objects.filter(alert_level='50pct').exists()

    def test_cutoff_activated_at_100pct(self):
        self._make_logs_totalling(301)  # 301/300 = 100.3%
        with patch.object(BudgetGuard, '_send_alert'):
            BudgetGuard().check()
        assert BudgetAlert.objects.filter(alert_level='100pct').exists()
        from django.core.cache import cache
        assert cache.get(BUDGET_CUTOFF_REDIS_KEY) is True

    def test_alert_not_duplicated_on_second_check(self):
        self._make_logs_totalling(160.0)
        with patch.object(BudgetGuard, '_send_alert'):
            BudgetGuard().check()
            BudgetGuard().check()  # second run
        assert BudgetAlert.objects.filter(alert_level='50pct').count() == 1

    def test_send_alert_skipped_without_founder_email(self):
        """No exception raised when FOUNDER_EMAIL is not set."""
        with patch.dict('os.environ', {'FOUNDER_EMAIL': ''}):
            guard = BudgetGuard()
            guard._send_alert('50pct', 155.0)  # should not raise


# ── Analytics API view tests ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestBudgetStatusView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/analytics/budget/'

    def test_returns_ok_when_no_spend(self):
        make_monthly_budget(cost='0.00')
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['status'] == 'ok'

    def test_returns_warning_at_50pct(self):
        make_monthly_budget(cost='150.00')
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['status'] == 'warning'

    def test_returns_critical_at_80pct(self):
        make_monthly_budget(cost='240.00')
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['status'] == 'critical'

    def test_returns_cutoff_at_100pct(self):
        make_monthly_budget(cost='300.00')
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['status'] == 'cutoff'

    def test_cutoff_active_field_present(self):
        make_monthly_budget(cost='10.00')
        resp = self.client.get(self.url)
        assert 'cutoff_active' in resp.data

    def test_cost_not_exposed_to_anonymous(self):
        make_monthly_budget(cost='250.00')
        resp = self.client.get(self.url)
        assert 'total_cost_usd' not in resp.data


@pytest.mark.django_db
class TestAnalyticsDashboardView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/analytics/dashboard/'

    def test_requires_admin(self):
        user = UserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        assert resp.status_code == 403

    def test_unauthenticated_blocked(self):
        resp = self.client.get(self.url)
        assert resp.status_code in (401, 403)

    def test_admin_gets_full_dashboard(self):
        admin = AdminUserFactory()
        session = DebateSessionFactory(user=admin)
        make_gpt_log(session)
        make_monthly_budget()
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert 'budget' in resp.data
        assert 'model_usage' in resp.data
        assert 'stage_distribution' in resp.data
        assert 'recent_logs' in resp.data
        assert 'budget_alerts' in resp.data

    def test_dashboard_budget_fields(self):
        admin = AdminUserFactory()
        make_monthly_budget(cost='60.00', tokens=2000, messages=10, sessions=3)
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        budget = resp.data['budget']
        assert budget['total_cost_usd'] == 60.0
        assert budget['monthly_limit_usd'] == 300.0
        assert budget['percent_used'] == 20.0
        assert budget['status'] == 'ok'
        assert budget['total_tokens'] == 2000
        assert budget['total_sessions'] == 3
        assert budget['total_messages'] == 10

    def test_model_usage_breakdown(self):
        admin = AdminUserFactory()
        session = DebateSessionFactory(user=admin)
        make_gpt_log(session, model='gpt-4o-mini', cost='0.001000')
        make_gpt_log(session, model='gpt-4o', cost='0.010000')
        make_monthly_budget()
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        models = [m['model_used'] for m in resp.data['model_usage']]
        assert 'gpt-4o-mini' in models
        assert 'gpt-4o' in models


@pytest.mark.django_db
class TestGPTLogListView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/analytics/logs/'

    def test_requires_admin(self):
        user = UserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        assert resp.status_code == 403

    def test_admin_sees_all_logs(self):
        admin = AdminUserFactory()
        session = DebateSessionFactory()
        make_gpt_log(session)
        make_gpt_log(session)
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['count'] == 2

    def test_filter_by_model(self):
        admin = AdminUserFactory()
        session = DebateSessionFactory()
        make_gpt_log(session, model='gpt-4o-mini')
        make_gpt_log(session, model='gpt-4o')
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url + '?model=gpt-4o-mini')
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['model_used'] == 'gpt-4o-mini'

    def test_filter_by_date_from(self):
        admin = AdminUserFactory()
        session = DebateSessionFactory()
        make_gpt_log(session)
        self.client.force_authenticate(user=admin)
        today = timezone.now().date().isoformat()
        resp = self.client.get(self.url + f'?from={today}')
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_pagination_present(self):
        admin = AdminUserFactory()
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        assert 'count' in resp.data
        assert 'results' in resp.data


@pytest.mark.django_db
class TestBudgetAlertListView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/analytics/alerts/'

    def test_requires_admin(self):
        user = UserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        assert resp.status_code == 403

    def test_admin_sees_alerts(self):
        admin = AdminUserFactory()
        now = timezone.now()
        BudgetAlert.objects.create(
            month=now.date().replace(day=1),
            total_cost_usd=Decimal('150.00'),
            alert_level='50pct',
        )
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['alert_level'] == '50pct'


@pytest.mark.django_db
class TestManualBudgetCheckView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/api/v1/analytics/budget/check/'

    def test_requires_admin(self):
        user = UserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.post(self.url)
        assert resp.status_code == 403

    def test_admin_can_trigger_check(self):
        admin = AdminUserFactory()
        self.client.force_authenticate(user=admin)
        with patch('analytics_app.budget_guard.BudgetGuard.check') as mock_check:
            resp = self.client.post(self.url)
        assert resp.status_code == 200
        assert 'message' in resp.data
        mock_check.assert_called_once()

    def test_returns_500_on_error(self):
        admin = AdminUserFactory()
        self.client.force_authenticate(user=admin)
        with patch('analytics_app.budget_guard.BudgetGuard.check', side_effect=Exception('DB down')):
            resp = self.client.post(self.url)
        assert resp.status_code == 500
        assert 'error' in resp.data