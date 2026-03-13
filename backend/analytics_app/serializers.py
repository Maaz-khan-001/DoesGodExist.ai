from rest_framework import serializers
from .models import GPTLog, BudgetAlert, MonthlyBudget


class GPTLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for admin GPT usage logs."""

    class Meta:
        model = GPTLog
        fields = [
            'id', 'session', 'model_used', 'routing_reason',
            'prompt_tokens', 'completion_tokens', 'total_tokens',
            'cost_usd', 'latency_ms', 'cache_hit', 'cache_layer',
            'created_at',
        ]
        read_only_fields = fields


class BudgetAlertSerializer(serializers.ModelSerializer):
    """Serializer for budget alert history."""

    class Meta:
        model = BudgetAlert
        fields = [
            'id', 'month', 'total_cost_usd', 'alert_level',
            'is_cutoff_active', 'created_at',
        ]
        read_only_fields = fields


class MonthlyBudgetSerializer(serializers.ModelSerializer):
    """
    Serializer for the monthly budget summary.
    Adds computed percent_used and status fields.
    """
    percent_used = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_percent_used(self, obj):
        import os
        limit = float(os.getenv('MONTHLY_BUDGET_USD', '300'))
        if limit <= 0:
            return 0
        return round(float(obj.total_cost_usd) / limit * 100, 1)

    def get_status(self, obj):
        pct = self.get_percent_used(obj)
        if pct >= 100:
            return 'cutoff'
        if pct >= 80:
            return 'critical'
        if pct >= 50:
            return 'warning'
        return 'ok'

    class Meta:
        model = MonthlyBudget
        fields = [
            'id', 'month', 'total_cost_usd', 'total_tokens',
            'total_sessions', 'total_messages',
            'percent_used', 'status', 'updated_at',
        ]
        read_only_fields = fields


class ModelUsageSerializer(serializers.Serializer):
    """Serializer for per-model usage breakdown in dashboard."""
    model_used = serializers.CharField()
    count = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=8)
    total_tokens = serializers.IntegerField()


class StageDistributionSerializer(serializers.Serializer):
    """Serializer for stage breakdown in dashboard."""
    current_stage = serializers.CharField()
    count = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    """
    Top-level dashboard serializer.
    Wraps all analytics data into a single response.
    """
    budget = MonthlyBudgetSerializer()
    model_usage = ModelUsageSerializer(many=True)
    stage_distribution = StageDistributionSerializer(many=True)
    recent_logs = GPTLogSerializer(many=True)
    budget_alerts = BudgetAlertSerializer(many=True)
