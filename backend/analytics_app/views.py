import os
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache

from .models import GPTLog, BudgetAlert, MonthlyBudget
from .serializers import (
    GPTLogSerializer, BudgetAlertSerializer,
    MonthlyBudgetSerializer, DashboardSerializer,
)
from .budget_guard import BUDGET_CUTOFF_REDIS_KEY

logger = logging.getLogger(__name__)

BUDGET_LIMIT = float(os.getenv('MONTHLY_BUDGET_USD', '300'))


def _get_or_refresh_monthly_budget(now=None):
    """
    Get the MonthlyBudget for the current month.
    Falls back to SUM aggregation if the record shows 0 cost
    (e.g. first call of the month before any spend).
    """
    if now is None:
        now = timezone.now()
    month_start = now.date().replace(day=1)

    monthly, created = MonthlyBudget.objects.get_or_create(
        month=month_start,
        defaults={'total_cost_usd': Decimal('0')}
    )

    # Sync from logs if MonthlyBudget looks empty but logs exist
    if monthly.total_cost_usd == 0:
        agg = GPTLog.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(
            total_cost=Sum('cost_usd'),
            total_tokens=Sum('total_tokens'),
            total_messages=Count('id'),
        )
        if agg['total_cost']:
            monthly.total_cost_usd = agg['total_cost']
            monthly.total_tokens = agg['total_tokens'] or 0
            monthly.total_messages = agg['total_messages'] or 0
            monthly.save(update_fields=[
                'total_cost_usd', 'total_tokens', 'total_messages'
            ])

    return monthly


class AnalyticsDashboardView(APIView):
    """
    GET /api/v1/analytics/dashboard/
    Admin-only. Full usage dashboard in one call.

    Response:
      {
        "budget": { current cost, limit, percent, status },
        "model_usage": [ { model, count, cost, tokens } ],
        "stage_distribution": [ { stage, count } ],
        "recent_logs": [ last 20 GPT calls ],
        "budget_alerts": [ alert history ]
      }
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        monthly = _get_or_refresh_monthly_budget(now)
        pct = float(monthly.total_cost_usd) / BUDGET_LIMIT * 100 if BUDGET_LIMIT else 0

        # Model usage breakdown
        model_usage = list(
            GPTLog.objects.filter(
                created_at__year=now.year,
                created_at__month=now.month,
            ).values('model_used').annotate(
                count=Count('id'),
                total_cost=Sum('cost_usd'),
                total_tokens=Sum('total_tokens'),
            ).order_by('-total_cost')
        )

        # Stage distribution (all time)
        from debate_app.models import DebateSession
        stage_dist = list(
            DebateSession.objects.filter(
                deleted_at__isnull=True
            ).values('current_stage').annotate(count=Count('id'))
        )

        # Recent GPT logs
        recent_logs = GPTLog.objects.select_related('session').order_by('-created_at')[:20]

        # Budget alert history
        month_start = now.date().replace(day=1)
        alerts = BudgetAlert.objects.filter(month=month_start).order_by('created_at')

        return Response({
            'budget': {
                'month': str(monthly.month),
                'total_cost_usd': float(monthly.total_cost_usd),
                'monthly_limit_usd': BUDGET_LIMIT,
                'percent_used': round(pct, 1),
                'status': MonthlyBudgetSerializer(monthly).data['status'],
                'cutoff_active': bool(cache.get(BUDGET_CUTOFF_REDIS_KEY)),
                'total_tokens': monthly.total_tokens,
                'total_sessions': monthly.total_sessions,
                'total_messages': monthly.total_messages,
            },
            'model_usage': model_usage,
            'stage_distribution': stage_dist,
            'recent_logs': GPTLogSerializer(recent_logs, many=True).data,
            'budget_alerts': BudgetAlertSerializer(alerts, many=True).data,
        })


class BudgetStatusView(APIView):
    """
    GET /api/v1/analytics/budget/

    Lightweight budget check.
    Used by the frontend to show a "high usage" warning banner.
    NOT admin-only — any authenticated user can see the status.
    (They don't see exact costs, just the status string.)
    """
    def get(self, request):
        monthly = _get_or_refresh_monthly_budget()
        pct = float(monthly.total_cost_usd) / BUDGET_LIMIT * 100 if BUDGET_LIMIT else 0

        if pct >= 100:
            status = 'cutoff'
        elif pct >= 80:
            status = 'critical'
        elif pct >= 50:
            status = 'warning'
        else:
            status = 'ok'

        return Response({
            'status': status,
            'cutoff_active': bool(cache.get(BUDGET_CUTOFF_REDIS_KEY)),
            # Don't expose exact cost to non-admins
        })


class GPTLogListView(APIView):
    """
    GET /api/v1/analytics/logs/
    Paginated list of GPT call logs. Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = GPTLog.objects.select_related('session').order_by('-created_at')

        # Optional filters
        model = request.query_params.get('model')
        if model:
            queryset = queryset.filter(model_used=model)

        date_from = request.query_params.get('from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(queryset, request)

        return paginator.get_paginated_response(
            GPTLogSerializer(page, many=True).data
        )


class BudgetAlertListView(APIView):
    """
    GET /api/v1/analytics/alerts/
    Budget alert history. Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        alerts = BudgetAlert.objects.order_by('-created_at')[:50]
        return Response(BudgetAlertSerializer(alerts, many=True).data)


class ManualBudgetCheckView(APIView):
    """
    POST /api/v1/analytics/budget/check/
    Trigger a budget check immediately (admin action).
    Useful after a spike in usage.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from analytics_app.budget_guard import BudgetGuard
        try:
            BudgetGuard().check()
            return Response({'message': 'Budget check completed.'})
        except Exception as e:
            logger.error(f'Manual budget check failed: {e}')
            return Response({'error': str(e)}, status=500)

