from django.urls import path
from .views import (
    AnalyticsDashboardView,
    BudgetStatusView,
    GPTLogListView,
    BudgetAlertListView,
    ManualBudgetCheckView,
)

urlpatterns = [
    # Main admin dashboard — all stats in one call
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),

    # Budget status only — lightweight, used by frontend to show warning banner
    path('budget/', BudgetStatusView.as_view(), name='analytics-budget'),

    # GPT usage log (paginated)
    path('logs/', GPTLogListView.as_view(), name='analytics-logs'),

    # Budget alert history
    path('alerts/', BudgetAlertListView.as_view(), name='analytics-alerts'),

    # Trigger budget check manually (admin action)
    path('budget/check/', ManualBudgetCheckView.as_view(), name='analytics-budget-check'),
]
