from django.contrib import admin
from .models import GPTLog, BudgetAlert


@admin.register(GPTLog)
class GPTLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'message', 'model_used', 'total_tokens', 'cost_usd', 'latency_ms', 'cache_hit', 'created_at')
    list_filter = ('model_used', 'cache_layer', 'cache_hit', 'created_at')
    search_fields = ('session__id', 'model_used', 'routing_reason')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost_usd', 'latency_ms')
    
    fieldsets = (
        (None, {'fields': ('id', 'session', 'message')}),
        ('Model Info', {'fields': ('model_used', 'routing_reason')}),
        ('Token Usage', {'fields': ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cost_usd')}),
        ('Performance', {'fields': ('latency_ms', 'prompt_hash', 'cache_layer', 'cache_hit')}),
        ('Error Info', {'fields': ('error',)}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['session', 'message'])
        return readonly


@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'total_cost_usd', 'alert_level', 'is_cutoff_active', 'created_at')
    list_filter = ('alert_level', 'is_cutoff_active', 'month')
    search_fields = ('month',)
    ordering = ('-month',)
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        (None, {'fields': ('id', 'month', 'alert_level')}),
        ('Budget Info', {'fields': ('total_cost_usd', 'is_cutoff_active')}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
