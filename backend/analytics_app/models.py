from django.db import models
from uuid import uuid4


class GPTLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    session = models.ForeignKey('debate_app.DebateSession', on_delete=models.PROTECT,
                                related_name='gpt_logs')
    message = models.ForeignKey('debate_app.Message', null=True, blank=True,
                                on_delete=models.SET_NULL)
    model_used = models.CharField(max_length=64)
    routing_reason = models.CharField(max_length=100, default='')
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    cost_usd = models.DecimalField(max_digits=8, decimal_places=6)
    latency_ms = models.IntegerField()
    prompt_hash = models.CharField(max_length=64, default='')
    cache_layer = models.CharField(max_length=10, null=True, blank=True)
    cache_hit = models.BooleanField(default=False)
    error = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['session']),
        ]


class BudgetAlert(models.Model):
    # UUID PK - consistent with all other tables (v2 incorrectly used AutoField)
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    month = models.DateField()
    total_cost_usd = models.DecimalField(max_digits=8, decimal_places=4)
    alert_level = models.CharField(max_length=10,
        choices=[('50pct','50%'),('80pct','80%'),('100pct','100%')])
    is_cutoff_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['month','alert_level']]
        
class MonthlyBudget(models.Model):
    month = models.DateField(unique=True)  # always the 1st of the month
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_tokens = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month']

    @property
    def status(self):
        from django.conf import settings
        import os
        limit = float(os.getenv('MONTHLY_BUDGET_USD', '300'))
        if not limit:
            return 'ok'
        pct = float(self.total_cost_usd) / limit * 100
        if pct >= 100:
            return 'cutoff'
        elif pct >= 80:
            return 'critical'
        elif pct >= 50:
            return 'warning'
        return 'ok'