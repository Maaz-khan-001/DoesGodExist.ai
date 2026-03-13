import os
import logging
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from .models import GPTLog, BudgetAlert

logger = logging.getLogger(__name__)

# This Redis key is the authoritative cutoff signal.
# It is read by orchestrator.py in every Gunicorn worker process.
BUDGET_CUTOFF_REDIS_KEY = 'budget:cutoff_active'
BUDGET_CUTOFF_TTL = 86400 * 35    # 35 days — persists past month boundary


class BudgetGuard:
    """
    Checks monthly GPT spending against MONTHLY_BUDGET_USD.
    Sends email alerts at 50%, 80%, 100%.
    At 100%: writes cutoff flag to Redis so ALL workers stop new debates.

    Run via Celery Beat (hourly_budget_check task in analytics/tasks.py).
    """
    LIMIT = float(os.getenv('MONTHLY_BUDGET_USD', '300'))
    THRESHOLDS = [0.5, 0.8, 1.0]

    def check(self):
        now = timezone.now()
        month_start = now.date().replace(day=1)

        # Sum all GPT costs this month
        total = GPTLog.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(t=Sum('cost_usd'))['t'] or Decimal('0')

        total_float = float(total)
        logger.info(f'Budget check: ${total_float:.4f} / ${self.LIMIT}')

        for threshold in self.THRESHOLDS:
            if total_float >= self.LIMIT * threshold:
                level = f'{int(threshold * 100)}pct'

                # Only create one alert record per threshold per month
                if not BudgetAlert.objects.filter(
                    month=month_start,
                    alert_level=level
                ).exists():
                    is_cutoff = (threshold >= 1.0)

                    BudgetAlert.objects.create(
                        month=month_start,
                        total_cost_usd=total,
                        alert_level=level,
                        is_cutoff_active=is_cutoff,
                    )

                    self._send_alert(level, total_float)

                    if is_cutoff:
                        # Write to Redis — visible to ALL Gunicorn workers
                        cache.set(BUDGET_CUTOFF_REDIS_KEY, True, BUDGET_CUTOFF_TTL)
                        logger.critical(
                            f'BUDGET CUTOFF ACTIVATED at ${total_float:.4f}. '
                            f'Redis key {BUDGET_CUTOFF_REDIS_KEY} set.'
                        )

    def _send_alert(self, level: str, total: float):
        founder_email = os.getenv('FOUNDER_EMAIL', '')
        if not founder_email:
            logger.warning('FOUNDER_EMAIL not set — budget alert email not sent.')
            return

        # Warn if email backend is console (common misconfiguration in production)
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in backend.lower():
            logger.warning(
                'EMAIL_BACKEND is console — budget alert will NOT be delivered. '
                'Set EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD '
                'in your .env and update settings.py to use SMTP backend in production.'
            )

        try:
            send_mail(
                subject=f'[DoesGodExist.ai] Budget Alert: {level} threshold reached',
                message=(
                    f'Monthly GPT cost has reached ${total:.4f}.\n'
                    f'Monthly budget: ${self.LIMIT}.\n'
                    f'Threshold: {level}\n\n'
                    f'Check your admin dashboard for details.'
                ),
                from_email='noreply@doesgodexist.ai',
                recipient_list=[founder_email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f'Failed to send budget alert email: {e}')
