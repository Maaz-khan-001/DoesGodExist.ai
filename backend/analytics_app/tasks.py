import logging
from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def hourly_budget_check():
    """
    Check monthly spending against budget thresholds.
    Sends alert emails at 50%, 80%, and 100%.
    Activates Redis cutoff flag at 100%.

    Scheduled: Every hour (crontab(minute=0))
    """
    from analytics_app.budget_guard import BudgetGuard
    try:
        BudgetGuard().check()
        logger.info('hourly_budget_check: complete')
    except Exception as e:
        logger.error(f'hourly_budget_check failed: {e}', exc_info=True)


@app.task
def daily_stats_aggregation():
    """
    Aggregate daily stats into MonthlyBudget record.
    Ensures MonthlyBudget stays in sync even if incremental
    updates were missed (e.g. during deploys or errors).

    Scheduled: Every day at 1am UTC (crontab(hour=1, minute=0))
    """
    from django.utils import timezone
    from django.db.models import Sum, Count
    from analytics_app.models import GPTLog, MonthlyBudget
    from debate_app.models import DebateSession

    now = timezone.now()
    month_start = now.date().replace(day=1)

    # Aggregate from raw logs
    agg = GPTLog.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
    ).aggregate(
        total_cost=Sum('cost_usd'),
        total_tokens=Sum('total_tokens'),
        total_messages=Count('id'),
    )

    session_count = DebateSession.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
        deleted_at__isnull=True,
    ).count()

    monthly, created = MonthlyBudget.objects.get_or_create(
        month=month_start,
        defaults={'total_cost_usd': 0}
    )

    from decimal import Decimal
    monthly.total_cost_usd = agg['total_cost'] or Decimal('0')
    monthly.total_tokens = agg['total_tokens'] or 0
    monthly.total_messages = agg['total_messages'] or 0
    monthly.total_sessions = session_count
    monthly.save()

    logger.info(
        f'daily_stats_aggregation: ${monthly.total_cost_usd:.4f} '
        f'| {monthly.total_tokens} tokens '
        f'| {monthly.total_messages} messages '
        f'| {monthly.total_sessions} sessions'
    )


@app.task
def increment_monthly_cost(cost_usd: float, tokens: int, is_new_session: bool = False):
    """
    Increment MonthlyBudget in real-time after each GPT call.
    Called from orchestrator after successful GPT response.

    This keeps MonthlyBudget in sync without needing expensive
    SUM queries on every budget check.

    Args:
      cost_usd:       Cost of this GPT call in USD
      tokens:         Total tokens used
      is_new_session: Whether this was the first message in a new session
    """
    from django.utils import timezone
    from django.db.models import F
    from analytics_app.models import MonthlyBudget
    from decimal import Decimal

    now = timezone.now()
    month_start = now.date().replace(day=1)

    update_fields = {
        'total_cost_usd': F('total_cost_usd') + Decimal(str(cost_usd)),
        'total_tokens': F('total_tokens') + tokens,
        'total_messages': F('total_messages') + 1,
    }
    if is_new_session:
        update_fields['total_sessions'] = F('total_sessions') + 1

    # get_or_create ensures the row exists, then update atomically
    monthly, created = MonthlyBudget.objects.get_or_create(
        month=month_start,
        defaults={'total_cost_usd': Decimal('0')}
    )

    MonthlyBudget.objects.filter(pk=monthly.pk).update(**update_fields)
